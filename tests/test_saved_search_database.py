"""Offline tests for database saved searches; never import cloud connection setup."""
import ast
from pathlib import Path
from unittest.mock import MagicMock
import unittest
from sqlalchemy import create_engine, text, bindparam

ROOT = Path(__file__).resolve().parents[1]


def functions(names, ns):
    tree = ast.parse((ROOT / 'db_functions.py').read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'db_functions.py', 'exec'), ns)


class SavedSearchDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as c:
            c.execute(text("ATTACH DATABASE ':memory:' AS public"))
            for sql in ['CREATE TABLE public.majors (cipcode INTEGER, cipdesc TEXT)',
                        'CREATE TABLE public.major_fav (user_id INTEGER, cipcode INTEGER)',
                        'CREATE TABLE public.major_rec (user_id INTEGER, cipcode INTEGER)',
                        "INSERT INTO public.majors VALUES (1,'Biology'),(2,'Chemistry'),(3,'Physics'),(4,'Art')",
                        'INSERT INTO public.major_fav VALUES (42,1),(42,2),(99,4)',
                        'INSERT INTO public.major_rec VALUES (42,2),(42,3),(99,4)']:
                c.execute(text(sql))
        self.ns = {'engine': self.engine, 'text': text, 'bindparam': bindparam}
        functions({'_normalize_search_list','resolve_search_major_codes','get_major_search_selection','get_search_major_labels'}, self.ns)

    def test_resolve_exact_names_and_codes_without_favorite_requirement(self):
        resolve = self.ns['resolve_search_major_codes']
        self.assertEqual(resolve(['Biology','1','Physics','3']), ['1','3'])
        self.assertEqual(resolve(['Art']), ['4'])
        self.assertEqual(self.ns['get_search_major_labels'](['1','3']), {'1':'Biology','3':'Physics'})
        for value in (['Unknown'], ['999'], [4], ['2147483648']):
            with self.assertRaises(ValueError): resolve(value)

    def test_union_and_empty_collection(self):
        select = self.ns['get_major_search_selection']
        self.assertEqual(select(42, saved=True, recs=True), [1,2,3])
        self.assertEqual(select(42, saved=True, majors=[3]), [1,2,3])
        self.assertEqual(select(77, saved=True), [])
        self.assertIsNone(select(None))
        with self.assertRaises(ValueError): select(None, recs=True)

    def test_save_materializes_major_list_and_binds_new_fields(self):
        import re
        mock = MagicMock()
        c = mock.begin.return_value.__enter__.return_value
        c.execute.return_value.scalar_one_or_none.return_value = 5
        # Real resolvers use the SQLite fixture; inserts are inspected, not executed.
        ns = {'engine':mock, 'text':text, 're':re,
              '_normalize_search_list':self.ns['_normalize_search_list'],
              'resolve_search_major_codes':self.ns['resolve_search_major_codes'],
              'get_major_search_selection':self.ns['get_major_search_selection']}
        functions({'save_major_search','save_program_search'},ns)
        result = ns['save_major_search'](42, saved=True, recs=True, search_text=' bio ', sort_order='earnings_desc')
        self.assertEqual(result, {'created':True,'id':5})
        sql, params = c.execute.call_args.args
        self.assertEqual(params['majors'], ['1','2','3'])
        self.assertEqual(params['search_text'],'bio')
        self.assertTrue(params['saved'])
        self.assertEqual(set(sql.compile().params),set(params))
        self.assertIn('created_at', str(sql))
        self.assertIn('CURRENT_TIMESTAMP', str(sql))
        ns['save_program_search'](42, majors=['Biology'], states=['ct','CT'], colleges=['College'], net_price_max=0)
        sql,params=c.execute.call_args.args
        self.assertEqual(params['states'],['CT'])
        self.assertEqual(params['majors'],['1'])
        self.assertEqual(params['sort_order'],'school_asc')
        self.assertEqual(params['net_price_max'],0)
        self.assertEqual(set(sql.compile().params),set(params))
        self.assertIn('created_at', str(sql))
        self.assertIn('CURRENT_TIMESTAMP', str(sql))
        for args in ({'sort_order':'bad'}, {'search_text':False}, {'states':['12345']}):
            with self.assertRaises(ValueError): ns['save_program_search'](42,**args)
        c.execute.return_value.scalar_one_or_none.return_value=None
        self.assertEqual(ns['save_major_search'](42)['created'],False)

    def test_restore_preserves_snapshot_zero_filters_and_lists(self):
        # Load the pure mapping module without initializing the Flask application.
        ns={}
        exec(compile((ROOT/'degree_path/saved_searches.py').read_text(),'saved_searches.py','exec'),ns)
        restore=ns['search_url_values']
        row={'majors':['1','3'],'saved':True,'recs':True,'search_text':'bio','sort_order':'name_desc','earnings_min':0}
        values=restore('majors',row)
        self.assertEqual(values['majors'],['1','3'])
        self.assertEqual(values['collection_snapshot'],1)
        self.assertEqual(values['saved'],1)
        self.assertEqual(values['earnings_min'],0)
        values=restore('programs',{'majors':['4'],'colleges':['A','B'],'states':['CT','NY'],'degrees':'2,3','net_price_max':0})
        self.assertEqual(values['major_filter'],'selected')
        self.assertEqual(values['state'],['CT','NY'])
        self.assertEqual(values['school_name'],['A','B'])
        self.assertEqual(values['degrees'],'2,3')
        self.assertEqual(values['net_price_max'],0)
        self.assertNotIn('degree_form',values)


    def test_latest_search_uses_timestamp_then_id_and_keeps_null_dates_last(self):
        functions({'get_all_major_search_filters','get_all_program_search_filters'}, self.ns)
        # Higher IDs deliberately have older or missing dates.
        common = 'id INTEGER, user_id INTEGER, majors TEXT, search_text TEXT, sort_order TEXT, created_at TEXT'
        with self.engine.begin() as c:
            c.execute(text('CREATE TABLE public.major_search (' + common + ', earnings_min INTEGER, saved BOOLEAN, recs BOOLEAN)'))
            c.execute(text('CREATE TABLE public.program_search (' + common + ', colleges TEXT, states TEXT, degrees TEXT, net_price_max INTEGER, tuition_in_max INTEGER, tuition_out_max INTEGER, acceptance_min INTEGER, acceptance_max INTEGER, satmt INTEGER, satvr INTEGER, satwr INTEGER, actmt INTEGER, acten INTEGER, actwr INTEGER)'))
            for table in ('major_search', 'program_search'):
                c.execute(text('INSERT INTO public.' + table + ' (id,user_id,created_at) VALUES (:id,:user_id,:created_at)'), [
                    {'id':1,'user_id':42,'created_at':'2026-11-10 12:00:00'},
                    {'id':2,'user_id':42,'created_at':'2026-11-10 12:00:00'},
                    {'id':9,'user_id':42,'created_at':'2026-11-09 12:00:00'},
                    {'id':20,'user_id':42,'created_at':None},
                    {'id':21,'user_id':42,'created_at':None},
                    {'id':30,'user_id':99,'created_at':'2026-11-11 12:00:00'},
                ])
        for kind in ('major','program'):
            rows = self.ns['get_all_' + kind + '_search_filters'](42)
            self.assertEqual([row['id'] for row in rows], [2,1,9,21,20])
            self.assertEqual(rows[0]['created_at'], '2026-11-10 12:00:00')
            self.assertEqual(self.ns['get_all_' + kind + '_search_filters'](77), [])
