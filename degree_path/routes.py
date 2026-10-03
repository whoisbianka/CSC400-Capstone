from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for
import re
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
def program_page(page=1, cipcode=None):
    import db_functions
    size = 25
    if type(page) is not int or not 1 <= page <= 100000:
        raise ValueError('Invalid page number.')
    if cipcode is None:
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
    data = program_page(page, cipcode)
    return render_template('explore.html', title='Explore programs', data=data, majors=catalog_majors(), cipcode=cipcode)

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