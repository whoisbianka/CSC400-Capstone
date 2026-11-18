"""Offline merge transaction tests with rollback-capable in-memory doubles."""
import ast
import json
from copy import deepcopy
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from sqlalchemy import text
from degree_path.evidence import evidence_list, merge_evidence

ROOT=Path(__file__).resolve().parents[1]

class GuestMergeTests(unittest.TestCase):
    def setUp(self):
        self.state={'guest': {'state': {
            'keywords':[{'keyword_id':1,'evidence':['Old','Guest','Guest']},{'keyword_id':2,'evidence':'Legacy guest'}],
            'messages':[{'role':'user','content':'Hello'}, {'role':'assistant','content':'Search',
                'metadata':{'explore_search':{'version':1,'filters':{'state':['MA']}}}}]}},
            'keywords':{1:['Old'],3:['Account only']}, 'messages':[], 'recommendations':[]}
        self.statements=[]
        def execute(query, params):
            sql=str(query);self.statements.append(sql)
            result=Mock()
            if 'FROM public.users' in sql: result.scalar_one_or_none.return_value=7
            elif 'SELECT state' in sql: result.mappings.return_value.one_or_none.return_value=deepcopy(self.state['guest'])
            elif 'SELECT keyword_id' in sql:
                result.mappings.return_value.all.return_value=[{'keyword_id':k,'evidence':v} for k,v in self.state['keywords'].items()]
            elif 'DELETE FROM public.guest_sessions' in sql: self.state['guest']=None
            else: raise AssertionError(sql)
            return result
        connection=SimpleNamespace(execute=execute)
        @contextmanager
        def begin():
            snapshot=deepcopy(self.state)
            try: yield connection
            except Exception:
                self.state=snapshot
                raise
        def insert(conn, table, columns, rows, **kwargs):
            if table=='user_keywords':
                for row in rows: self.state['keywords'][row['keyword_id']]=row['evidence']
            elif table=='chatlog': self.state['messages'].extend(deepcopy(rows))
            else: raise AssertionError(table)
        def refresh(conn, uid, *, saved_keywords):
            self.state['recommendations']=deepcopy(saved_keywords)
        self.refresh=Mock(side_effect=refresh)
        ns=dict(engine=SimpleNamespace(begin=begin), text=text, json=json, evidence_list=evidence_list,
                merge_evidence=merge_evidence, _insert_chat_rows=insert, _refresh_user_recommendations=self.refresh)
        nodes=[n for n in ast.parse((ROOT/'db_functions.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='merge_guest_into_user']
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'db_functions.py','exec'),ns)
        self.merge=ns['merge_guest_into_user']

    def test_union_order_metadata_and_repeat_login(self):
        self.assertTrue(self.merge(7,'guest'))
        self.assertEqual(self.state['keywords'],{1:['Old','Guest'],2:['Legacy guest'],3:['Account only']})
        self.assertEqual([m['sender'] for m in self.state['messages']],['user','assistant'])
        metadata=json.loads(self.state['messages'][1]['metadata'])
        self.assertEqual(metadata['explore_search']['filters']['state'],['MA'])
        self.assertEqual({k['keyword_id'] for k in self.state['recommendations']},{1,2,3})
        self.assertIsNone(self.state['guest'])
        self.assertFalse(self.merge(7,'guest'))
        self.assertEqual(len(self.state['messages']),2)
        self.assertIn('FOR UPDATE',self.statements[0])
        self.assertIn('FOR UPDATE',self.statements[1])
        self.assertIn('expires_at > CURRENT_TIMESTAMP',self.statements[1])
        self.assertFalse(any('fav' in sql or 'program_search' in sql for sql in self.statements))

    def test_failure_rolls_back_all_imports_and_allows_retry(self):
        before=deepcopy(self.state)
        self.refresh.side_effect=RuntimeError('ranking failed')
        with self.assertRaises(RuntimeError): self.merge(7,'guest')
        self.assertEqual(self.state,before)
        self.refresh.side_effect=None
        self.assertTrue(self.merge(7,'guest'))

    def test_missing_or_expired_session_is_noop(self):
        self.state['guest']=None
        before=deepcopy(self.state)
        self.assertFalse(self.merge(7,'guest'))
        self.assertEqual(self.state,before)
        self.refresh.assert_not_called()

    def test_guest_turn_accumulates_evidence_and_preserves_old_keywords(self):
        from degree_path.chat_schemas import AdvisorTurn, KeywordAddition
        nodes=[n for n in ast.parse((ROOT/'degree_path/routes.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='apply_guest_chat_turn']
        ns=dict(deepcopy=deepcopy, evidence_list=evidence_list, merge_evidence=merge_evidence)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'routes.py','exec'),ns)
        state={'messages':[], 'keywords':[{'keyword_id':1,'keyword':'Biology','evidence':'Old'}]}
        turn=AdvisorTurn(reply='Okay',keyword_additions=[KeywordAddition(keyword_id=1,evidence=['New','Old'])],keyword_removals=[],major_mentions=[])
        updated=ns['apply_guest_chat_turn'](state,'New',turn,[{'keyword_id':1,'keyword':'Biology'}])
        self.assertEqual(updated['keywords'][0]['evidence'],['Old','New'])
        self.assertEqual(state['keywords'][0]['evidence'],'Old')

    def test_evidence_rejects_non_strings_and_preserves_full_messages(self):
        self.assertEqual(merge_evidence(['First\nmessage'],'Second'),['First\nmessage','Second'])
        with self.assertRaises(ValueError): evidence_list([123])
