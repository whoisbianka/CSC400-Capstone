"""Account verification and comparison use existing saved-major storage."""
import unittest
from sqlalchemy import text
from test_favorites import FavoritesTests


class ProfileComparisonTests(FavoritesTests):
    def catalog(self):
        with self.engine.begin() as c:
            c.execute(text("INSERT INTO majors VALUES (5202, 'Business Administration')"))
            c.execute(text('CREATE TABLE schools (unitid INTEGER PRIMARY KEY, instnm TEXT, city TEXT, stabbr TEXT)'))
            c.execute(text("INSERT INTO schools VALUES (1,'Elmwood','New Haven','CT'),(2,'Westbridge','Hartford','CT')"))
            c.execute(text('CREATE TABLE programs (program_id INTEGER PRIMARY KEY, unitid INTEGER, cipcode INTEGER, credlev INTEGER)'))
            c.execute(text('INSERT INTO programs VALUES (1,1,1107,3),(2,2,5202,3)'))
            c.execute(text('CREATE TABLE cost_info (id INTEGER PRIMARY KEY, unitid INTEGER, npt4 INTEGER, npt43 INTEGER, tuitionfee_in INTEGER, tuitionfee_out INTEGER)'))
            c.execute(text('INSERT INTO cost_info VALUES (1,1,15000,11000,12000,28000),(2,2,21000,16000,18000,26000)'))
            c.execute(text('CREATE TABLE adm_crit (id INTEGER PRIMARY KEY, unitid INTEGER, adm_rate NUMERIC, satmt25 INTEGER, satmt75 INTEGER, satvr25 INTEGER, satvr75 INTEGER, actmt25 INTEGER, actmt75 INTEGER, acten25 INTEGER, acten75 INTEGER)'))
            c.execute(text('CREATE TABLE program_rank_crit (id INTEGER PRIMARY KEY, program_id INTEGER, earn_mdn_4yr_nat INTEGER)'))
            c.execute(text('INSERT INTO program_rank_crit VALUES (1,1,82000),(2,2,65000)'))
        self.save(cipcode=1107)
        self.save(cipcode=5202)

    def test_account_identity_is_server_verified(self):
        self.assertEqual(self.client.get('/api/account').status_code, 401)
        self.assertEqual(self.client.get('/api/account', headers={'Authorization': 'Bearer forged'}).status_code, 401)
        response = self.client.get('/api/account', headers=self.headers())
        self.assertEqual(response.json, {'verified': True, 'provider': 'Clerk', 'clerk_user_id': 'user_alice'})
        self.assertEqual(self.client.get('/api/account', headers=self.headers(exp=1)).status_code, 401)

    def test_profile_has_verified_state_and_saved_majors_link(self):
        page = self.client.get('/profile').data
        self.assertIn(b'js/account.js', page)
        self.assertIn(b'js/profile.js', page)
        self.assertIn(b'id="profile-signed-in" hidden', page)
        self.assertIn(b'View saved majors &amp; compare', page)
        self.assertNotIn(b'Coming soon', page)

    def test_two_saved_majors_have_real_programs_and_account_isolation(self):
        self.catalog()
        response = self.client.get('/api/saved-majors/programs', headers=self.headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['majors']), 2)
        self.assertEqual({p['program_id'] for group in response.json['majors'] for p in group['programs']}, {1, 2})
        self.assertEqual(self.client.get('/api/saved-majors/programs', headers=self.headers('user_bob')).json['majors'], [])
        self.assertEqual(self.client.get('/api/saved-majors/1107/programs', headers=self.headers('user_bob')).status_code, 404)

    def test_existing_major_fav_saves_are_used_for_comparison(self):
        self.catalog()
        with self.engine.begin() as c:
            c.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY, clerk_user_id TEXT)'))
            c.execute(text("INSERT INTO users VALUES (17,'user_alice'),(18,'user_bob')"))
            c.execute(text('CREATE TABLE major_fav (user_id INTEGER, cipcode INTEGER)'))
            c.execute(text('INSERT INTO major_fav VALUES (17,1107),(17,5202)'))
        self.app.extensions['favorites_storage'] = 'major_fav'
        result = self.client.get('/api/saved-majors/programs', headers=self.headers()).json
        self.assertEqual({m['cipcode'] for m in result['majors']}, {1107, 5202})
        self.assertEqual(self.client.get('/api/saved-majors/programs', headers=self.headers('user_bob')).json['majors'], [])

    def test_saved_page_loads_comparison_and_open_button(self):
        page = self.client.get('/saved-majors').data
        self.assertIn(b'js/saved-majors.js', page)
        self.assertIn(b'id="saved-open-comparison"', page)
        self.assertIn(b'id="saved-comparison-results" hidden', page)
        self.assertNotIn(b'<select', page)


if __name__ == '__main__':
    unittest.main()
