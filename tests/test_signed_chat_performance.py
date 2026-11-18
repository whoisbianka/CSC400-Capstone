"""Offline tests of chat SQL orchestration; never connects to a database."""
from degree_path.evidence import evidence_list, merge_evidence
import ast
import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from sqlalchemy import text, bindparam


class SignedChatPerformanceTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        source = root / 'db_functions.py'
        if not source.exists():
            source = Path(__file__).with_name('db_functions.py')
        names = {'save_chat_turn', '_insert_chat_rows', '_refresh_user_recommendations', 'get_chat_state'}
        nodes = [n for n in ast.parse(source.read_text()).body
                 if isinstance(n, ast.FunctionDef) and n.name in names]
        self.connection = Mock()
        self.statements = []
        self.rows = [{'keyword_id': 1, 'evidence': 'Old evidence'}]
        def execute(statement, params):
            self.statements.append((str(statement), params))
            result = Mock()
            result.scalar_one_or_none.return_value = 7
            result.mappings.return_value.all.return_value = self.rows
            return result
        self.connection.execute.side_effect = execute
        self.scope = dict(
            evidence_list=evidence_list, merge_evidence=merge_evidence, json=json, text=text, bindparam=bindparam, engine=SimpleNamespace(
                begin=Mock(side_effect=lambda: nullcontext(self.connection)),
                connect=Mock(side_effect=lambda: nullcontext(self.connection))),
            timed_step=lambda name: nullcontext(),
            timed_connection=Mock(side_effect=lambda *args, **kwargs: nullcontext(self.connection)),
            get_recommendations=Mock(return_value=[{'cipcode': 26, 'evidence': 'Updated evidence'}]),
            _rank_majors_from_keywords=Mock(return_value=[
                {'cipcode': 26, 'matching_keywords': 1},
                {'cipcode': 27, 'matching_keywords': 1},
            ]),
            get_recent_chatlog=Mock(return_value=[]), get_user_keywords=Mock(return_value=[]),
        )
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), self.scope)

    def save(self, additions=(), removals=()):
        turn = SimpleNamespace(reply='Assistant reply', keyword_additions=list(additions), keyword_removals=list(removals))
        return self.scope['save_chat_turn'](7, 'User message', turn)

    def test_unchanged_keywords_reuse_and_batch_messages(self):
        self.save()
        self.scope['_rank_majors_from_keywords'].assert_not_called()
        self.assertIn('FOR UPDATE', self.statements[0][0])
        self.assertIn('SELECT keyword_id', self.statements[1][0])
        insert = next(item for item in self.statements if 'INSERT INTO public.chatlog' in item[0])
        self.assertIn('), (', insert[0])
        self.assertIsInstance(insert[1], dict)
        self.assertEqual(insert[1]['p_0_sender'], 'user')
        self.assertEqual(insert[1]['p_1_sender'], 'assistant')
        self.assertFalse(any('DELETE FROM public.major_rec' in sql for sql, _ in self.statements))

    def test_evidence_only_update_does_not_rerank(self):
        result = self.save([SimpleNamespace(keyword_id=1, evidence='Updated evidence')])
        self.scope['_rank_majors_from_keywords'].assert_not_called()
        self.scope['get_recommendations'].assert_called_once_with(7, connection=self.connection)
        upsert = next(item for item in self.statements if 'INSERT INTO public.user_keywords' in item[0])
        self.assertEqual(upsert[1]['p_0_evidence'], ['Old evidence', 'Updated evidence'])
        self.assertIn('ON CONFLICT', upsert[0])
        self.assertEqual(result[0]['evidence'], 'Updated evidence')

    def test_added_keywords_rerank_and_batch_recommendations(self):
        self.save([SimpleNamespace(keyword_id=2, evidence="User's new interest")])
        args = self.scope['_rank_majors_from_keywords'].call_args.args
        self.assertEqual({row['keyword_id'] for row in args[1]}, {1, 2})
        inserts = [item for item in self.statements if 'INSERT INTO public.major_rec' in item[0]]
        self.assertEqual(len(inserts), 1)
        self.assertIn('), (', inserts[0][0])
        self.assertEqual(sum('SELECT keyword_id' in sql for sql, _ in self.statements), 1)
        self.assertNotIn("User's new interest", ''.join(sql for sql, _ in self.statements))

    def test_removal_and_missing_recommendations(self):
        self.save(removals=[1])
        self.assertEqual(self.scope['_rank_majors_from_keywords'].call_args.args[1], [])
        self.assertTrue(any('DELETE FROM public.user_keywords' in sql for sql, _ in self.statements))
        self.scope['_rank_majors_from_keywords'].reset_mock()
        self.scope['get_recommendations'].return_value = []
        self.save()
        self.scope['_rank_majors_from_keywords'].assert_called_once()

    def test_unchanged_evidence_skips_upsert(self):
        self.save([SimpleNamespace(keyword_id=1, evidence='Old evidence')])
        self.assertFalse(any('INSERT INTO public.user_keywords' in sql for sql, _ in self.statements))

    def test_state_reads_share_one_connection(self):
        result = self.scope['get_chat_state'](7, include_recommendations=True)
        self.scope['engine'].connect.assert_called_once()
        for name in ('get_recent_chatlog', 'get_user_keywords', 'get_recommendations'):
            self.scope[name].assert_called_once_with(7, connection=self.connection)
        self.assertIn('recommendations', result)

    def test_statement_failure_propagates(self):
        self.connection.execute.side_effect = RuntimeError('database failed')
        with self.assertRaises(RuntimeError):
            self.save()
        self.scope['_rank_majors_from_keywords'].assert_not_called()



    def test_search_metadata_is_bound_as_json_in_same_chat_insert(self):
        metadata = {'explore_search': {'version': 1, 'filters': {'state': ['MA']}}}
        turn = SimpleNamespace(reply='Explore programs', keyword_additions=[], keyword_removals=[])
        self.scope['save_chat_turn'](7, 'Find programs', turn, metadata=metadata)
        sql, params = next(item for item in self.statements if 'INSERT INTO public.chatlog' in item[0])
        self.assertIn('CAST(:p_1_metadata AS JSONB)', sql)
        self.assertEqual(json.loads(params['p_1_metadata']), metadata)
        self.assertEqual(json.loads(params['p_0_metadata']), {})
