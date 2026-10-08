from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for
import re
import secrets
from urllib.parse import urlsplit #added this bc the explore programs page was making requests to the database 25 different times for each card
from functools import wraps
from werkzeug.exceptions import HTTPException

def database_errors(function):
    """Return an unavailable response when a database query fails."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except HTTPException:
            raise
        except Exception:
            abort(503, description='Database unavailable. Check authentication, certificates, connection settings, and schema.')
    return wrapped

def normalize(value):
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', value.lower()).split())

def college_website_url(value):
    if not value:
        return None
    value = str(value).strip()
    if any(character.isspace() for character in value):
        return None
    if '://' not in value and not value.startswith('//'):
        if ':' in value:
            return None
        value = 'https://' + value
    elif value.startswith('//'):
        value = 'https:' + value
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() in ('http', 'https') and parts.hostname and not parts.username and not parts.password:
            return value
    except ValueError:
        pass
    return None


@database_errors
def catalog_majors():
    # Import on a database request, after create_app loads .env and certificates.
    import db_functions
    from flask import g
    if 'catalog_majors' not in g:
        g.catalog_majors = sorted(
            ({'cipcode': int(row.cipcode), 'name': row.cipdesc}
             for row in db_functions.scan_entire_table('majors', 5000)),
            key=lambda row: row['name'].casefold(),
        )
    return g.catalog_majors


@database_errors
def program_page(page=1, cipcode=None, degrees=None, filters=None, shuffle_seed=None):
    import db_functions
    size = 25
    if type(page) is not int or not 1 <= page <= 100000:
        raise ValueError('Invalid page number.')
    if degrees is not None:
        from sqlalchemy import text
        if any(degree not in (2, 3) for degree in degrees):
            raise ValueError('Invalid degree level.')
        # Apply degree and major selections before selecting a bounded page.
        conditions = (['p.credlev IN (' + ', '.join(f':degree_{i}' for i in range(len(degrees))) + ')']
                      if degrees else ['1 = 1'])
        params = {f'degree_{i}': degree for i, degree in enumerate(degrees)}
        if cipcode is not None:
            conditions.append('p.cipcode = :cipcode')
            params['cipcode'] = cipcode
        filters = filters or {}
        for key, column in [('state', 's.stabbr'), ('city', 's.city')]:
            if filters.get(key):
                conditions.append(f'LOWER({column}) = LOWER(:{key})')
                params[key] = filters[key]
        for table, alias, join, specs in [
            ('cost_info', 'c', 'c.unitid = p.unitid',
             [('net_price_max', 'npt4', '<='), ('tuition_in_max', 'tuitionfee_in', '<='),
              ('tuition_out_max', 'tuitionfee_out', '<=')]),
            ('adm_crit', 'a', 'a.unitid = p.unitid',
             [('acceptance_min', 'adm_rate', '>='), ('acceptance_max', 'adm_rate', '<=')])
        ]:
            clauses = []
            for key, column, operator in specs:
                if key in filters:
                    clauses.append(f'{alias}.{column} {operator} :{key}')
                    params[key] = filters[key] / 100 if key.startswith('acceptance_') else filters[key]
            if clauses:
                conditions.append(f'EXISTS (SELECT 1 FROM {table} {alias} WHERE {join} AND '
                                  + ' AND '.join(clauses) + ')')
        params.update(limit=size + 1, offset=(page - 1) * size)
        ordering = 'p.program_id ASC'
        if shuffle_seed is not None:
            params['shuffle_seed'] = shuffle_seed
            # A seeded hash shuffles the whole result set consistently across pages.
            ordering = "md5(CAST(p.program_id AS TEXT) || :shuffle_seed), p.program_id ASC"
        query = text('SELECT p.program_id, p.unitid, p.cipcode FROM programs p '
                     'JOIN schools s ON s.unitid = p.unitid WHERE '
                     + ' AND '.join(conditions)
                     + ' ORDER BY ' + ordering + ' LIMIT :limit OFFSET :offset')
        with db_functions.engine.connect() as connection:
            matches = connection.execute(query, params).mappings().all()
        records = matches[:size]
        more = len(matches) > size
    elif cipcode is None:
        records = db_functions.get_a_page(page, size, 'programs', 'program_id', 'ASC')
        # One extra bounded lookup establishes whether Next should appear.
        more = bool(db_functions.get_a_page(page * size + 1, 1, 'programs', 'program_id', 'ASC'))
    else:
        # The unchanged function returns all matches for one major.
        # Slice AFTER sorting so page order stays deterministic.
        matches = sorted(db_functions.get_programs_from_cipcode(cipcode), key=lambda r: r['program_id'])
        offset = (page - 1) * size
        records = matches[offset:offset + size]
        more = len(matches) > offset + size
    # Fetch card facts for this page in one bounded query; omit absent values.
    facts = {}
    if degrees is not None and records:
        from sqlalchemy import bindparam, text
        columns = ['p.program_id', 'p.credlev',
                   '(SELECT s.insturl FROM schools s WHERE s.unitid = p.unitid LIMIT 1) AS website']
        for table, alias, fields in [
            ('cost_info', 'c', ('npt4', 'tuitionfee_in', 'tuitionfee_out')),
            ('adm_crit', 'a', ('adm_rate', 'satmt25', 'satmt75', 'satvr25', 'satvr75', 'actmt25', 'actmt75', 'acten25', 'acten75')),
        ]:
            columns.extend(f'(SELECT {alias}.{field} FROM {table} {alias} '
                           f'WHERE {alias}.unitid = p.unitid ORDER BY {alias}.id LIMIT 1) AS {field}'
                           for field in fields)
        query = text('SELECT ' + ', '.join(columns)
                     + ' FROM programs p WHERE p.program_id IN :ids').bindparams(bindparam('ids', expanding=True))
        with db_functions.engine.connect() as connection:
            facts = {int(row['program_id']): dict(row) for row in
                     connection.execute(query, {'ids': [record['program_id'] for record in records]}).mappings()}
    for fact in facts.values():
        fact['website'] = college_website_url(fact.get('website'))
    names = {m['cipcode']: m['name'] for m in catalog_majors()}
    schools = {}
    rows = []
    for record in records:
        unitid = record['unitid']
        if unitid not in schools:
            schools[unitid] = db_functions.get_city_state(unitid).get(str(unitid), {})
        school = schools[unitid]
        rows.append({
            'id': int(record['program_id']), 'unitid': unitid,
            'cipcode': record['cipcode'],
            'major': names.get(record['cipcode'], f"CIP {record['cipcode']}"),
            'college': school.get('instnm', 'Not available'),
            'city': school.get('city'), 'state': school.get('stabbr'),
            'facts': facts.get(int(record['program_id']), {}),
        })
    return {'rows': rows, 'page': page, 'has_next': more}

@database_errors
def program(program_id):
    import db_functions
    if type(program_id) is not int or not 0 < program_id <= 2147483647:
        return None
    try:
        identifiers = db_functions.get_unit_and_cip_from_program_id(program_id)
    except UnboundLocalError:
        return None
    if identifiers is None:
        return None
    unitid, cipcode = identifiers
    names = {m['cipcode']: m['name'] for m in catalog_majors()}
    # Original helpers return dictionaries keyed by the UNITID as a string.
    school = db_functions.get_city_state(unitid).get(str(unitid), {})
    costs = db_functions.get_cost_info(unitid).get(str(unitid), {})
    sat = db_functions.get_sat_crit(unitid).get(str(unitid), {})
    # In the unchanged file the second definition returns ACT fields only.
    act = db_functions.get_school_adm_crit(unitid).get(str(unitid), {})
    try:
        earnings = db_functions.get_mdn_earnings(program_id)
    except UnboundLocalError:
        earnings = None
    return {
        'id': program_id, 'unitid': unitid, 'cipcode': cipcode,
        'major': names.get(cipcode, f'CIP {cipcode}'),
        'college': school.get('instnm', 'Not available'),
        'city': school.get('city'), 'state': school.get('stabbr'),
        'earnings': earnings, 'costs': costs, 'sat': sat, 'act': act,
    }

@database_errors
def recommendations(terms):
    import db_functions
    # Only resolve actual catalog major names. Interest-to-major rules remain
    # in the teammate's JS, clearly described there as exploration prompts.
    terms = list(dict.fromkeys(normalize(t) for t in terms if normalize(t)))
    candidates = []
    for major in catalog_majors():
        name = normalize(major['name'])
        if any(f' {term} ' in f' {name} ' for term in terms):
            candidates.append(major)
    candidates.sort(key=lambda m: (normalize(m['name']) not in terms, m['name'].casefold()))
    output = []
    for major in candidates[:6]:
        records = db_functions.get_best_progs_from_cip(3, major['cipcode'], 'earn_mdn_4yr_nat')
        # The unchanged helper does NOT return program_id. Never invent links.
        output.append({
            **major,
            'programs': [{'college': r['School'], 'major': r['Major'],
                          'earnings': r['Earnings']} for r in records],
        })
    return {'majors': output, 'has_more': len(candidates) > 6,
            'note': 'Examples ranked by reported median earnings, not personal fit. Location and cost preferences have not been applied.'}

web = Blueprint('web', __name__)

def positive_arg(name, default=None, maximum=2147483647):
    value = request.args.get(name)
    if value is None or value == '':
        return default
    try:
        number = int(value)
    except ValueError:
        abort(400, description=f'Invalid {name}.')
    if not 1 <= number <= maximum:
        abort(400, description=f'Invalid {name}.')
    return number

def text_value(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 200:
        abort(400, description='Enter a major name between 1 and 200 characters.')
    return value.strip()

@web.get('/')
def home():
    return render_template('home.html')


@web.post('/')
@web.route('/chat', methods=['GET', 'POST'])
def chat():
    question = ''
    result = None
    if request.method == 'POST':
        question = text_value(request.form.get('question'))
        result = recommendations([question])
    return render_template('chat.html', title='Degree Path Assistant', question=question, result=result)


@web.post('/chat/reset')
def reset_chat():
    return redirect(url_for('web.chat'), code=303)

@web.get('/questionnaire')
def questionnaire():
    return render_template('guided_chat.html', title='Find my major')

@web.get('/explore')
def explore():
    page = positive_arg('page', 1, 100000)
    cipcode = positive_arg('cipcode')
    # No selected degrees means no degree restriction.
    degree_values = (request.args.getlist('degree') if 'degree_form' in request.args
                     else request.args.get('degrees', '').split(','))
    if any(value not in ('', '2', '3') for value in degree_values):
        abort(400, description='Invalid degree level.')
    degrees = tuple(sorted({int(value) for value in degree_values if value}))
    filters = {}
    for key in ('state', 'city'):
        value = request.args.get(key, '').strip()
        if value:
            if len(value) > (3 if key == 'state' else 100):
                abort(400, description='Invalid location filter.')
            filters[key] = value
    for key in ('net_price_max', 'tuition_in_max', 'tuition_out_max',
                'acceptance_min', 'acceptance_max'):
        value = request.args.get(key, '').strip()
        if value:
            try:
                number = int(value)
            except ValueError:
                abort(400, description='Filters must use whole numbers.')
            if not 0 <= number <= (100 if key.startswith('acceptance_') else 2147483647):
                abort(400, description='Filter value is out of range.')
            filters[key] = number
    for prefix in ('acceptance',):
        if filters.get(prefix + '_min', 0) > filters.get(prefix + '_max', 2147483647):
            abort(400, description='Minimum must not exceed maximum.')
    if 'explore_shuffle_seed' not in session:
        session['explore_shuffle_seed'] = secrets.token_hex(16)
    data = program_page(page, cipcode, degrees, filters, session['explore_shuffle_seed'])
    return render_template('explore.html', title='Explore programs', data=data,
                           majors=catalog_majors(), cipcode=cipcode, degrees=degrees,
                           degree_query=','.join(map(str, degrees)), filters=filters)

@web.get('/programs/<int:program_id>')
def program_details(program_id):
    details = program(program_id)
    if details is None:
        abort(404, description='Program not found.')
    return render_template('program_details.html', title=details['major'], program=details)

@web.get('/start/<destination>')
def start(destination):
    destinations = {'questionnaire': ('web.questionnaire', 'Find my path'),
                    'explore': ('web.explore', 'Explore majors')}
    if destination not in destinations:
        abort(404)
    endpoint, label = destinations[destination]
    return render_template('start.html', title='Choose how to continue',
                           destination_url=url_for(endpoint), destination_label=label)


@web.get('/profile')
def profile():
    return render_template('profile.html', title='Profile')


@web.get('/settings')
def settings():
    return render_template('settings.html', title='Settings')


@web.get('/<page>.html')
def legacy_page(page):
    targets = {'index': 'web.home', 'chatbot': 'web.questionnaire',
               'explore': 'web.explore', 'program-details': 'web.explore',
               'profile': 'web.profile', 'settings': 'web.settings'}
    if page not in targets:
        abort(404)
    target = 'web.questionnaire' if page == 'index' and request.args.get('mode') == 'guided' else targets[page]
    return redirect(url_for(target))


@web.get('/api/health')
def health():
    return jsonify(status='ok', engine='python', framework='flask')

@web.get('/api/programs')
def programs_api():
    data = program_page(positive_arg('page', 1, 100000), positive_arg('cipcode'))
    return jsonify(programs=data['rows'], page=data['page'], has_next=data['has_next'], page_size=25)

@web.post('/api/search')
def search_api():
    if not request.is_json:
        abort(415, description='Send JSON.')
    body = request.get_json()
    if not isinstance(body, dict):
        abort(400, description='Send an object containing a major name in question.')
    return jsonify(recommendations([text_value(body.get('question'))]))

@web.post('/api/recommendations')
def recommendations_api():
    if not request.is_json:
        abort(415, description='Send JSON.')
    body = request.get_json()
    if not isinstance(body, dict) or not isinstance(body.get('majors'), list):
        abort(400, description='Send a majors list.')
    if not 1 <= len(body['majors']) <= 20:
        abort(400, description='Send between 1 and 20 major names.')
    terms = [text_value(term) for term in body['majors']]
    return jsonify(recommendations(terms))