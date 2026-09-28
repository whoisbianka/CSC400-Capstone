"""Map database-branch's public catalog tables to the application's program records."""
from ..services.search import STATES

STATE_CODES = 'AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()
STATE_NAMES = {**dict(zip(STATE_CODES, STATES)), 'DC': 'District of Columbia', 'PR': 'Puerto Rico', 'GU': 'Guam', 'VI': 'Virgin Islands', 'AS': 'American Samoa', 'MP': 'Northern Mariana Islands'}

# cost_info has no uniqueness constraint on unitid. Select the highest inserted cost_id
# deterministically so duplicate imports cannot multiply the program rows.
CATALOG_SQL = '''
SELECT p.program_id, p.credlev, s.instnm, s.stabbr, s.city,
       m.cipdesc, c.tuitionfee_in, c.tuitionfee_out
FROM public.programs p
JOIN public.schools s ON s.unitid = p.unitid
JOIN public.majors m ON m.cipcode = p.cipcode
LEFT JOIN public.cost_info c ON c.unitid = p.unitid
    AND c.cost_id = (SELECT MAX(c2.cost_id) FROM public.cost_info c2 WHERE c2.unitid = p.unitid)
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

    def all(self):
        return [self._normalize(row) for row in self.database.select(CATALOG_SQL + ' ORDER BY p.program_id')]

    def get(self, program_id):
        if not program_id.isascii() or not program_id.isdigit() or len(program_id) > 10:
            return None
        identifier = int(program_id)
        if not 0 < identifier <= 2147483647:
            return None
        rows = self.database.select(CATALOG_SQL + ' WHERE p.program_id = :program_id', {'program_id': identifier})
        return self._normalize(rows[0]) if rows else None
