"""Actual comparison queries with isolated catalog data and verified test sessions."""
import sys
import time
import unittest
from types import ModuleType
from unittest.mock import patch
from sqlalchemy import create_engine, text


class SavedComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modules = patch.dict(sys.modules, {'db_functions': ModuleType('db_functions')})
        cls.modules.start()
        cls.addClassCleanup(cls.modules.stop)
        from degree_path import create_app
        cls.app = create_app({'TESTING':True,'SECRET_KEY':'offline-only','CLERK_SECRET_KEY':'offline',
            'CLERK_PUBLISHABLE_KEY':'pk_test_offline','CLERK_AUTHORIZED_PARTIES':['http://localhost']})

    def setUp(self):
        self.client = self.app.test_client()
        self.engine = create_engine('sqlite://')
        self.addCleanup(self.engine.dispose)
        p = patch('degree_path.saved_comparison.comparison_engine', return_value=self.engine)
        p.start();self.addCleanup(p.stop)
        with self.engine.begin() as c:
            c.execute(text('CREATE TABLE majors (cipcode INTEGER PRIMARY KEY, cipdesc TEXT)'))
            c.execute(text("INSERT INTO majors VALUES (1107,'Computer Science'),(2601,'Biology'),(4201,'Psychology')"))
            c.execute(text('CREATE TABLE major_fav (id INTEGER PRIMARY KEY,user_id INTEGER,cipcode INTEGER)'))
            c.execute(text('INSERT INTO major_fav VALUES (1,42,1107),(2,42,2601),(3,99,4201)'))
            c.execute(text('CREATE TABLE schools (unitid INTEGER PRIMARY KEY,instnm TEXT,city TEXT,stabbr TEXT)'))
            c.execute(text("INSERT INTO schools VALUES (1,'Elmwood','New Haven','CT'),(2,'Westbridge','Hartford','CT')"))
            c.execute(text('CREATE TABLE programs (program_id INTEGER PRIMARY KEY,unitid INTEGER,cipcode INTEGER,credlev INTEGER)'))
            c.execute(text('CREATE TABLE cost_info (id INTEGER PRIMARY KEY,unitid INTEGER,npt4 INTEGER,npt43 INTEGER,tuitionfee_in INTEGER,tuitionfee_out INTEGER)'))
            c.execute(text('INSERT INTO cost_info VALUES (1,1,15400,11800,12900,28700),(2,1,99999,99999,99999,99999),(3,2,-1,NULL,0,26400)'))
            c.execute(text('CREATE TABLE adm_crit (id INTEGER PRIMARY KEY,unitid INTEGER,adm_rate NUMERIC,satmt25 INTEGER,satmt75 INTEGER,satvr25 INTEGER,satvr75 INTEGER,actmt25 INTEGER,actmt75 INTEGER,acten25 INTEGER,acten75 INTEGER)'))
            c.execute(text('INSERT INTO adm_crit VALUES (1,1,0.76,990,1190,1000,1200,20,25,21,26)'))
            c.execute(text('CREATE TABLE program_rank_crit (id INTEGER PRIMARY KEY,program_id INTEGER,earn_mdn_4yr_nat INTEGER)'))
            for i in range(1,7):
                c.execute(text('INSERT INTO programs VALUES (:id,:school,1107,3)'),{'id':i,'school':1 if i<4 else 2})
                c.execute(text('INSERT INTO program_rank_crit VALUES (:id,:id,:earnings)'),{'id':i,'earnings':80000+i})
            c.execute(text('INSERT INTO programs VALUES (99,1,4201,3)'))

    def login(self, user=42):
        with self.client.session_transaction() as s:
            s.update(user_id=user,clerk_user_id=f'user_{user}',login_expires_at=int(time.time())+3600)

    def test_guest_and_stale_account_rejected(self):
        self.assertEqual(self.client.get('/api/saved-majors/programs').status_code,401)
        self.assertEqual(self.client.get('/api/saved-majors/1107/programs').status_code,401)
        self.login()
        self.assertEqual(self.client.get('/api/saved-majors/programs',headers={'X-App-User-ID':'99'}).status_code,401)

    def test_real_programs_and_pagination_with_suppressed_or_duplicate_facts(self):
        self.login()
        response=self.client.get('/api/saved-majors/programs')
        self.assertEqual(response.status_code,200)
        groups={m['cipcode']:m for m in response.json['majors']}
        self.assertEqual(set(groups),{1107,2601})
        self.assertEqual(groups[2601]['programs'],[])
        cs=groups[1107]
        self.assertEqual([p['program_id'] for p in cs['programs']],[1,2,3,4])
        self.assertTrue(cs['has_next'])
        self.assertEqual(cs['programs'][0]['npt4'],15400)
        self.assertEqual(cs['programs'][0]['earnings'],80001)
        self.assertEqual(cs['programs'][0]['adm_rate'],0.76)
        self.assertIsNone(cs['programs'][3]['npt4'])
        self.assertIsNone(cs['programs'][3]['adm_rate'])
        self.assertEqual(cs['programs'][3]['tuitionfee_in'],0)
        next_page=self.client.get('/api/saved-majors/1107/programs?page=2').json
        self.assertEqual([p['program_id'] for p in next_page['programs']],[5,6])
        self.assertFalse(next_page['has_next'])

    def test_only_session_owners_favorites_are_returned(self):
        self.login(99)
        response=self.client.get('/api/saved-majors/programs?user_id=42')
        self.assertEqual([g['cipcode'] for g in response.json['majors']],[4201])
        self.assertEqual(self.client.get('/api/saved-majors/1107/programs').status_code,404)

    def test_empty_account_and_removed_major(self):
        self.login(100)
        self.assertEqual(self.client.get('/api/saved-majors/programs').json,{'majors':[]})
        self.login()
        with self.engine.begin() as c:c.execute(text('DELETE FROM major_fav WHERE user_id=42 AND cipcode=1107'))
        self.assertEqual(self.client.get('/api/saved-majors/1107/programs').status_code,404)

    def test_page_validation_and_template_includes_new_controller(self):
        self.login()
        for page in ('0','-1','oops','100001'):
            self.assertEqual(self.client.get('/api/saved-majors/1107/programs?page='+page).status_code,400)
        page=self.client.get('/saved-majors')
        self.assertEqual(page.status_code,200)
        for marker in (b'css/saved-majors.css',b'js/saved-majors.js',b'js/saved-major-controls.js',b'id="saved-comparison" class="saved-comparison" hidden'):
            self.assertIn(marker,page.data)


if __name__=='__main__':unittest.main()
