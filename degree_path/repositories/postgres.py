"""Map database-branch's public catalog tables to the application's program records."""
from ..services.search import STATES

STATE_CODES = 'AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()
STATE_NAMES = {**dict(zip(STATE_CODES, STATES)), 'DC': 'District of Columbia', 'PR': 'Puerto Rico', 'GU': 'Guam', 'VI': 'Virgin Islands', 'AS': 'American Samoa', 'MP': 'Northern Mariana Islands'}

# cost_info has no uniqueness constraint on unitid. Select the highest inserted id
# deterministically so duplicate imports cannot multiply the program rows.
CATALOG_SQL = '''
SELECT p.id AS row_id, p.program_id, p.credlev, s.instnm, s.stabbr, s.city,
       m.cipdesc, c.tuitionfee_in, c.tuitionfee_out
FROM public.programs p
JOIN public.schools s ON s.unitid = p.unitid
JOIN public.majors m ON m.cipcode = p.cipcode
LEFT JOIN (
    SELECT unitid, MAX(id) AS id
    FROM public.cost_info
    GROUP BY unitid
) latest_cost ON latest_cost.unitid = p.unitid
LEFT JOIN public.cost_info c ON c.id = latest_cost.id
'''


class PostgresProgramRepository:
    is_demo = False
    source_note = 'Database catalog · Confirm program availability and costs with the college. Study format and college type are not supplied by this schema.'

    def __init__(self, database, tuition_basis='in_state'):
        if tuition_basis not in ('in_state', 'out_of_state'):
            raise ValueError('TUITION_BASIS must be in_state or out_of_state.')
        self.database = database
        self.tuition_basis = tuition_basis
        self.tuition_label = 'Annual ' + ('in-state' if tuition_basis == 'in_state' else 'out-of-state') + ' tuition and fees (institution-level)'

    def _normalize(self, row):
        code = (row['stabbr'] or '').strip().upper()
        cost = row['tuitionfee_in' if self.tuition_basis == 'in_state' else 'tuitionfee_out']
        return {
            'id': str(row['program_id']), 'college': row['instnm'], 'major': row['cipdesc'],
            'state': STATE_NAMES.get(code, code), 'stateCode': code, 'city': row['city'] or '',
            'type': '', 'format': '', 'tuition': float(cost) if cost is not None and cost >= 0 else None,
            'keywords': [], 'careers': [], 'tuitionLabel': self.tuition_label,
            'degree': {2: "Associate's degree", 3: "Bachelor's degree"}.get(row['credlev'], 'Not available'),
        }

    def scan_entire_catalog(self, batch_size=2000):
        if type(batch_size) is not int or not 1 <= batch_size <= 5000:
            raise ValueError('batch_size must be between 1 and 5000.')
        last_id = 0
        while True:
            rows = self.database.select(
                CATALOG_SQL + ' WHERE p.id > :last_id ORDER BY p.id LIMIT :limit',
                {'last_id': last_id, 'limit': batch_size})
            if not rows:
                break
            for row in rows:
                yield self._normalize(row)
            last_id = rows[-1]['row_id']

    def all(self):
        return list(self.scan_entire_catalog())

    def suggested_majors(self):
        rows = self.database.select(
            'SELECT DISTINCT m.cipdesc FROM public.majors m '
            'JOIN public.programs p ON p.cipcode = m.cipcode '
            'ORDER BY m.cipdesc LIMIT 3')
        return [row['cipdesc'] for row in rows]

    def page(self, page=1, page_size=50, query='', sort='college', direction='asc', study_format=''):
        if type(page) is not int or not 1 <= page <= 1000000:
            raise ValueError('page must be between 1 and 1000000.')
        if type(page_size) is not int or not 1 <= page_size <= 100:
            raise ValueError('page_size must be between 1 and 100.')
        cost = 'c.tuitionfee_in' if self.tuition_basis == 'in_state' else 'c.tuitionfee_out'
        # Only fixed identifiers enter SQL; user text and paging values are bound.
        column = {'college': 'LOWER(s.instnm)', 'major': 'LOWER(m.cipdesc)',
                  'state': 's.stabbr', 'tuition': f'CASE WHEN {cost} >= 0 THEN {cost} END'}.get(sort, 'LOWER(s.instnm)')
        order = 'DESC' if direction == 'desc' else 'ASC'
        query = query.strip().lower()[:2000]
        escaped = query.replace('!', '!!').replace('%', '!%').replace('_', '!_')
        params = {'query': '%' + escaped + '%', 'limit': page_size + 1, 'offset': (page - 1) * page_size}
        where = " WHERE (LOWER(COALESCE(s.instnm, '') || ' ' || COALESCE(m.cipdesc, '') || ' ' || COALESCE(s.stabbr, '') || ' ' || COALESCE(s.city, '')) LIKE :query ESCAPE '!'"
        state_codes = [code for code, name in STATE_NAMES.items() if query and query in name.lower()]
        for index, code in enumerate(state_codes):
            key = f'state_{index}'
            where += f' OR s.stabbr = :{key}'
            params[key] = code
        where += ')'
        if study_format:
            where += ' AND 1 = 0'
        rows = self.database.select(CATALOG_SQL + where +
            f' ORDER BY {column} {order} NULLS LAST, p.id ASC LIMIT :limit OFFSET :offset', params)
        return {'rows': [self._normalize(row) for row in rows[:page_size]],
                'page': page, 'page_size': page_size, 'has_next': len(rows) > page_size}


    def get(self, program_id):
        if not program_id.isascii() or not program_id.isdigit() or len(program_id) > 10:
            return None
        identifier = int(program_id)
        if not 0 < identifier <= 2147483647:
            return None
        rows = self.database.select(CATALOG_SQL + ' WHERE p.program_id = :program_id', {'program_id': identifier})
        return self._normalize(rows[0]) if rows else None
