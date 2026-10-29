from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for
from .gemini_service import ask_gemini
import re
import secrets
from urllib.parse import urlsplit
from functools import wraps
from werkzeug.exceptions import HTTPException
from time import perf_counter

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

def format_program_cards(data):
    fact_fields = (
        "credlev",
        "npt4", "tuitionfee_in", "tuitionfee_out",
        "adm_rate",
        "satmt25", "satmt75", "satvr25", "satvr75",
        "actmt25", "actmt75", "acten25", "acten75",
    )

    cards = []

    for row in data["rows"]:
        facts = {
            field: row.get(field)
            for field in fact_fields
        }

        facts["website"] = college_website_url(row.get("website"))

        cards.append({
            "id": row["id"],
            "unitid": row["unitid"],
            "cipcode": row["cipcode"],
            "major": row["major"],
            "college": row["college"],
            "city": row["city"],
            "state": row["state"],
            "earnings": row.get("earnings"),
            "facts": facts,
        })

    return {
        "rows": cards,
        "page": data["page"],
        "has_next": data["has_next"],
    }

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
    search_filters={**(filters or {}),
                    "cipcode":cipcode,
                    "degrees":degrees}
    try:
        data=db_functions.get_page_programs(
            page=page,
            page_count=25,
            filters=search_filters,
            sort_option="school_name",
            sort_order="ASC"
            )
    except ValueError as error:
        abort(400, description=str(error))
    return format_program_cards(data)

    

@database_errors
def program(program_id):
    import db_functions

    if type(program_id) is not int or not 1 <= program_id <= 2147483647:
        return None

    row = db_functions.get_a_program(program_id)

    if row is None:
        return None

    cost_fields = (
        "npt4", "npt41", "npt42", "npt43", "npt44", "npt45",
        "tuitionfee_in", "tuitionfee_out",
    )

    sat_fields = (
        "satmt25", "satmt75",
        "satvr25", "satvr75",
        "satwr25", "satwr75",
    )

    act_fields = (
        "actmt25", "actmt75",
        "acten25", "acten75",
        "actwr25", "actwr75",
    )

    return {
        "id": row["id"],
        "unitid": row["unitid"],
        "cipcode": row["cipcode"],
        "major": row["major"],
        "college": row["college"],
        "city": row["city"],
        "state": row["state"],
        "earnings": row["earnings"],
        "costs": {key: row.get(key) for key in cost_fields},
        "sat": {key: row.get(key) for key in sat_fields},
        "act": {key: row.get(key) for key in act_fields},
        "description": (row.get("description") or "").strip(),
        "description_source": (
            row.get("description_source") or ""
        ).strip(),
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
    query = request.args.get('q', '').strip()
    if len(query) > 200:
        abort(400, description='Search must be at most 200 characters.')
    # No selected degrees means no degree restriction.
    degree_values = (request.args.getlist('degree') if 'degree_form' in request.args
                     else request.args.get('degrees', '').split(','))
    if any(value not in ('', '2', '3') for value in degree_values):
        abort(400, description='Invalid degree level.')
    degrees = tuple(sorted({int(value) for value in degree_values if value}))
    filters = {}
    if query:
        filters['q'] = query
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
    major_name=None
    if cipcode is not None and data["rows"]:
        major_name=data["rows"][0]["major"]
    # Build removal links from validated filters, resetting pagination only.
    active_params = {**filters}
    if cipcode is not None:
        active_params['cipcode'] = cipcode
    if degrees:
        active_params['degrees'] = ','.join(map(str, degrees))
    filter_chips = []

    def add_chip(label, key, replacement=None):
        remaining = {**active_params}
        remaining.pop(key, None)
        if replacement:
            remaining[key] = replacement
        filter_chips.append({'label': label, 'url': url_for('web.explore', **remaining)})

    labels = {'q': 'Search', 'state': 'State', 'city': 'City',
              'net_price_max': 'Cost after aid up to', 'tuition_in_max': 'In-state tuition up to',
              'tuition_out_max': 'Out-of-state tuition up to',
              'acceptance_min': 'Acceptance at least', 'acceptance_max': 'Acceptance up to'}
    for key, value in filters.items():
        display = (f'${value:,}' if key.endswith('_max') and not key.startswith('acceptance_')
                   else f'{value}%' if key.startswith('acceptance_') else str(value))
        add_chip(f'{labels[key]}: {display}', key)
    if cipcode is not None:
        add_chip(major_name or 'Selected major', 'cipcode')
    for degree in degrees:
        add_chip('Associate degree' if degree == 2 else 'Bachelor’s degree', 'degrees',
                 ','.join(str(other) for other in degrees if other != degree))
    return render_template('explore.html', title='Explore programs', data=data,
                           major_name=major_name, cipcode=cipcode, degrees=degrees,
                           degree_query=','.join(map(str, degrees)), filters=filters,
                           filter_chips=filter_chips)

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


@web.post('/api/gemini')
def gemini_api():
    # Make sure the request contains JSON
    if not request.is_json:
        return jsonify(error="Please send JSON."), 415

    data = request.get_json(silent=True)

    # Validate the student's question
    if not isinstance(data, dict):
        return jsonify(error="Invalid request."), 400

    question = data.get("question")

    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 500:
        return jsonify(error="Enter a question between 1 and 500 characters."), 400

    try:
        # Send the student's question to Google Gemini
        answer = ask_gemini(question.strip())

        # Return Gemini's response to the website
        return jsonify(response=answer)

    except Exception:
        current_app.logger.exception("Gemini request failed")
        return jsonify(error="The AI assistant is temporarily unavailable."), 503
