"""Exercise the actual comparison SQL offline, using SQLite fixtures."""
import ast
from decimal import Decimal
from pathlib import Path
import unittest
from sqlalchemy import create_engine, text, bindparam
from time import perf_counter
from degree_path.comparison import comparison_payload


class ComparisonDataTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        self.addCleanup(self.engine.dispose)
        names = {'get_saved_major_summaries', 'get_major_catalog_page', 'get_page_programs', 'validate_program_filters', 'get_major_name_suggestions', 'get_program_favorites', 'get_comparison_favorites', 'is_program_favorite', 'add_program_fav', 'remove_school_fav'}
        source = ast.parse((Path(__file__).resolve().parents[1] / 'db_functions.py').read_text())
        # Load the production functions without initializing a cloud connection.
        tree = ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in names], type_ignores=[])
        self.functions = {'engine': self.engine, 'text': text, 'bindparam': bindparam, 'perf_counter': perf_counter}
        exec(compile(tree, 'db_functions.py', 'exec'), self.functions)
        with self.engine.begin() as c:
            c.execute(text("ATTACH DATABASE ':memory:' AS public"))
            definitions = {
                'majors': 'cipcode INTEGER PRIMARY KEY, cipdesc TEXT',
                'major_info': 'cipcode INTEGER UNIQUE, mdn_earnings INTEGER, major_description TEXT, description_source TEXT',
                'major_fav': 'user_id INTEGER, cipcode INTEGER, UNIQUE(user_id, cipcode)',
                'program_fav': 'user_id INTEGER, program_id INTEGER, UNIQUE(user_id, program_id)',
                'programs': 'program_id INTEGER PRIMARY KEY, unitid INTEGER, cipcode INTEGER, credlev INTEGER',
                'schools': 'unitid INTEGER PRIMARY KEY, instnm TEXT, city TEXT, stabbr TEXT, ug12mn INTEGER, insturl TEXT',
                'program_rank_crit': 'program_id INTEGER UNIQUE, earn_mdn_4yr_nat INTEGER, earn_count_wne_4yr_nat INTEGER',
                'cost_info': 'unitid INTEGER UNIQUE, ' + ', '.join(k+' INTEGER' for k in ['npt4','npt41','npt42','npt43','npt44','npt45','tuitionfee_in','tuitionfee_out']),
                'adm_crit': 'unitid INTEGER UNIQUE, adm_rate NUMERIC, ' + ', '.join(k+suffix+' INTEGER' for k in ['satmt','satvr','satwr','actmt','acten','actwr'] for suffix in ['25','75']),
            }
            for table, columns in definitions.items():
                c.execute(text(f'CREATE TABLE public.{table} ({columns})'))
            for statement in [
                "INSERT INTO public.majors VALUES (7, 'Biology'), (8, 'Art')",
                "INSERT INTO public.schools VALUES (1, 'College', 'City', 'NY', 100, NULL)",
                "INSERT INTO public.programs VALUES (10, 1, 7, 3), (11, 1, 7, 5)",
                "INSERT INTO public.major_fav VALUES (42, 7), (99, 8)",
                "INSERT INTO public.program_fav VALUES (42, 10), (99, 11)",
            ]:
                c.execute(text(statement))

    def test_saved_major_summaries_are_general_and_account_owned(self):
        summaries = self.functions['get_saved_major_summaries'](42)
        self.assertEqual([m['cipcode'] for m in summaries], [7])
        self.assertEqual(summaries[0]['major'], 'Biology')
        self.assertEqual(summaries[0]['program_count'], 2)
        self.assertEqual(summaries[0]['school_count'], 1)
        self.assertIsNone(summaries[0]['description'])
        self.assertNotIn('programs', summaries[0])
        self.assertNotIn('college', summaries[0])
        other = self.functions['get_saved_major_summaries'](99)
        self.assertEqual([m['cipcode'] for m in other], [8])
        self.assertEqual(other[0]['program_count'], 0)
        self.assertEqual(self.functions['get_saved_major_summaries'](12345), [])

    def test_only_owned_favorites_and_missing_optional_data(self):
        majors = self.functions['get_comparison_favorites'](42, 'majors')
        self.assertEqual([m['id'] for m in majors], [7])
        self.assertIsNone(majors[0]['earnings'])
        self.assertEqual(majors[0]['program_count'], 2)
        self.assertEqual(majors[0]['school_count'], 1)
        programs = self.functions['get_comparison_favorites'](42, 'programs')
        self.assertEqual([p['id'] for p in programs], [10])
        self.assertIsNone(programs[0]['npt4'])
        self.assertEqual(self.functions['get_comparison_favorites'](123, 'majors'), [])
        with self.assertRaises(ValueError):
            self.functions['get_comparison_favorites'](42, 'unknown')

    def test_program_save_is_idempotent_and_removal_is_scoped(self):
        add = self.functions['add_program_fav']
        self.assertTrue(add(42, 11))
        self.assertTrue(add(42, 11))
        self.assertFalse(add(42, 999))
        self.assertEqual(len(self.functions['get_comparison_favorites'](42, 'programs')), 2)
        self.functions['remove_school_fav'](42, 11)
        self.assertFalse(self.functions['is_program_favorite'](42, 11))
        self.assertTrue(self.functions['is_program_favorite'](99, 11))

    def test_program_favorites_list_is_scoped_and_preserves_credential(self):
        rows = self.functions['get_program_favorites'](42)
        self.assertEqual([row['program_id'] for row in rows], [10])
        self.assertEqual(rows[0]['credlev'], 3)
        self.assertEqual(rows[0]['major'], 'Biology')
        self.assertEqual(self.functions['get_program_favorites'](123), [])

    def test_decimal_rates_and_partial_scores(self):
        data = comparison_payload('programs', [{'id': 10, 'credlev': 3, 'adm_rate': Decimal('0.5000'), 'satmt25': 1000, 'satmt75': None}])
        item = data['items'][0]
        self.assertEqual(item['adm_rate'], .5)
        self.assertEqual(item['satmt'], [1000, None])
        self.assertEqual(item['credential'], 'Bachelor’s degree')
        directions = {m['key']: m['direction'] for m in data['metrics']}
        self.assertEqual(directions['npt4'], 'lower')
        self.assertIsNone(directions['adm_rate'])
        self.assertNotIn('earnings_count', directions)

    def test_program_major_filters_exact_name_union_and_empty(self):
        with self.engine.begin() as c:
            c.execute(text("INSERT INTO public.programs VALUES (12, 1, 8, 3)"))
            c.execute(text("INSERT INTO public.cost_info (unitid, npt4) VALUES (1, 5000)"))
        get = self.functions['get_page_programs']
        ids = lambda result: [row['id'] for row in result['rows']]
        self.assertEqual(ids(get(filters={'major_name': 'biology'})), [10, 11])
        self.assertEqual(ids(get(filters={'major_name': 'Bio'})), [])
        self.assertEqual(ids(get(filters={'major_name': "Biology' OR 1=1 --"})), [])
        self.assertEqual(ids(get(filters={'cipcodes': [7, 8]})), [10, 11, 12])
        self.assertEqual(ids(get(filters={'cipcodes': []})), [])
        self.assertEqual(ids(get(filters={'cipcodes': [7], 'degrees': [3], 'net_price_max': 6000})), [10])
        self.assertEqual(ids(get(filters={'cipcodes': [7], 'net_price_max': 4000})), [])
        first = get(page_count=1, filters={'cipcodes': [7]})
        second = get(page=2, page_count=1, filters={'cipcodes': [7]})
        self.assertTrue(first['has_next'])
        self.assertEqual(ids(first), [10])
        self.assertEqual(ids(second), [11])
        self.assertFalse(second['has_next'])
        for filters in [{'cipcodes': '7'}, {'cipcodes': [True]}, {'cipcodes': [-1]}, {'major_name': ''}]:
            with self.assertRaises(ValueError):
                get(filters=filters)

    def test_major_suggestions_match_names_and_escape_wildcards(self):
        search = self.functions['get_major_name_suggestions']
        self.assertEqual(search('bio'), [{'cipcode': 7, 'name': 'Biology'}])
        self.assertEqual(search('%'), [])
        self.assertEqual(search('_'), [])

    def test_major_catalog_filters_sort_pagination_and_user_scope(self):
        with self.engine.begin() as c:
            c.execute(text("INSERT INTO public.major_info (cipcode, mdn_earnings) VALUES (7, 60000), (8, 40000)"))
            c.execute(text("INSERT INTO public.majors VALUES (9, 'Zoology')"))
        get = self.functions['get_major_catalog_page']
        ids = lambda result: [row['cipcode'] for row in result['rows']]
        self.assertEqual(ids(get()), [8, 7, 9])
        self.assertEqual(ids(get(query='bio')), [7])
        self.assertEqual(ids(get(query='%')), [])
        self.assertEqual(ids(get(sort='earnings_desc')), [7, 8, 9])
        self.assertEqual(ids(get(sort='earnings_asc')), [8, 7, 9])
        self.assertEqual(ids(get(earnings_min=50000)), [7])
        self.assertEqual(ids(get(has_programs=True)), [7])
        self.assertEqual(ids(get(favorites_only=True, user_id=42)), [7])
        self.assertEqual(ids(get(favorites_only=True, user_id=99)), [8])
        self.assertTrue(get(query='bio', user_id=42)['rows'][0]['is_favorite'])
        self.assertFalse(get(query='bio')['rows'][0]['is_favorite'])
        first = get(page_count=1)
        second = get(page=2, page_count=1)
        self.assertTrue(first['has_next'])
        self.assertEqual(ids(first), [8])
        self.assertEqual(ids(second), [7])
        for kwargs in [{'sort': 'DROP TABLE'}, {'favorites_only': True}, {'earnings_min': -1}, {'query': 'a'*201}]:
            with self.assertRaises(ValueError):
                get(**kwargs)

    def test_program_school_search_and_sort_remain_program_specific(self):
        with self.engine.begin() as c:
            c.execute(text("INSERT INTO public.program_rank_crit (program_id, earn_mdn_4yr_nat) VALUES (10, 20000), (11, 30000)"))
        get = self.functions['get_page_programs']
        rows = get(filters={'school_name': 'coll', 'cipcodes': [7]}, sort_option='earnings', sort_order='DESC')['rows']
        self.assertEqual([row['id'] for row in rows], [11, 10])
        self.assertEqual(get(filters={'school_name': '%'})['rows'], [])
