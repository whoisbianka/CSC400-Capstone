from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for

web = Blueprint('web', __name__)

def database_ui():
    return current_app.extensions['database_ui']

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
        result = database_ui().recommendations([question])
    return render_template('chat.html', title='Degree Path Assistant', question=question, result=result)


@web.post('/chat/reset')
def reset_chat():
    state()['history'] = []
    return redirect(url_for('web.chat'), code=303)

@web.get('/questionnaire')
def questionnaire():
    return render_template('guided_chat.html', title='Find my major')

@web.get('/explore')
def explore():
    page = positive_arg('page', 1, 100000)
    cipcode = positive_arg('cipcode')
    data = database_ui().program_page(page, cipcode)
    return render_template('explore.html', title='Explore programs', data=data, majors=database_ui().majors(), cipcode=cipcode)


@web.get('/programs/<program_id>')
def program_details(program_id):
    program = repository().get(program_id)
    if program is None:
        abort(404, description='This program is not in the current catalog.')
    return render_template('program_details.html', title=program['major'], program=program)


@web.get('/questionnaire')
def questionnaire():
    return render_template('guided_chat.html', title='Find my major')

@web.get('/programs/<int:program_id>')
def program_details(program_id):
    program = database_ui().program(program_id)
    if program is None:
        abort(404, description='Program not found.')
    return render_template('program_details.html', title=program['major'], program=program)

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
    data = database_ui().program_page(positive_arg('page', 1, 100000), positive_arg('cipcode'))
    return jsonify(programs=data['rows'], page=data['page'], has_next=data['has_next'], page_size=25)

@web.post('/api/search')
def search_api():
    if not request.is_json:
        abort(415, description='Send JSON.')
    body = request.get_json()
    if not isinstance(body, dict):
        abort(400, description='Send an object containing a major name in question.')
    return jsonify(database_ui().recommendations([text_value(body.get('question'))]))

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
    return jsonify(database_ui().recommendations(terms))