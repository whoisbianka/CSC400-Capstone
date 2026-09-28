"""Page routes and the compatible public demo API."""
import secrets
import time
from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for
from .services.search import search
from .services.catalog import filter_programs, SORTS, FORMATS
from .services.questionnaire import QUESTIONS, next_step, results, validate_text

web = Blueprint('web', __name__)


def repository():
    return current_app.extensions['program_repository']


def search_options():
    repo = repository()
    return {'demo': repo.is_demo, 'tuition_label': repo.tuition_label}


def state():
    # Local demo only: opaque browser cookie, answers/history in process memory.
    # Expire inactive sessions after two hours and retain at most 256 browsers.
    store = current_app.extensions['demo_states']
    now = time.monotonic()
    for key, value in list(store.items()):
        if now - value['seen'] > 7200:
            store.pop(key, None)
    sid = session.get('demo_id')
    if sid not in store:
        sid = secrets.token_urlsafe(24)
        session['demo_id'] = sid
        store[sid] = {'answers': {}, 'history': [], 'seen': now}
    store.move_to_end(sid)
    while len(store) > 256:
        store.popitem(last=False)
    store[sid]['seen'] = now
    return store[sid]


def table_context(programs):
    return {'rows': filter_programs(programs, request.args), 'sorts': SORTS, 'formats': FORMATS if repository().is_demo else ()}


@web.route('/', methods=['GET', 'POST'])
def chat():
    data = state()
    question, error = '', None
    if request.method == 'POST':
        question = request.form.get('question', '')
        error = validate_text(question)
        if not error:
            data['history'].append({'question': question.strip(), 'result': search(question, repository().all(), **search_options())})
            data['history'] = data['history'][-10:]
            return redirect(url_for('web.chat', _anchor='latest-result'), code=303)
    majors = list(dict.fromkeys(p['major'] for p in repository().all()))[:3]
    return render_template('chat.html', title='Degree Path Assistant', history=data['history'], question=question,
                           error=error, suggestions=[f'Which colleges offer {m}?' for m in majors]), 400 if error else 200


@web.post('/chat/reset')
def reset_chat():
    state()['history'] = []
    return redirect(url_for('web.chat'), code=303)


@web.get('/explore')
def explore():
    return render_template('explore.html', title='Explore', **table_context(repository().all()))


@web.get('/programs/<program_id>')
def program_details(program_id):
    program = repository().get(program_id)
    if program is None:
        abort(404, description='This program is not in the current catalog.')
    return render_template('program_details.html', title=program['major'], program=program)


@web.get('/questionnaire')
def questionnaire():
    step = next_step(state()['answers'])
    return redirect(url_for('web.review' if step is None else 'web.question', **({} if step is None else {'step': step})))


@web.route('/questionnaire/<int:step>', methods=['GET', 'POST'])
def question(step):
    if not 0 <= step < len(QUESTIONS):
        abort(404)
    answers = state()['answers']
    key, prompt = QUESTIONS[step]
    answer, error = answers.get(key, ''), None
    if request.method == 'POST':
        answer = request.form.get('answer', '')
        error = validate_text(answer)
        if not error:
            answers[key] = answer.strip()
            return redirect(url_for('web.questionnaire'), code=303)
    return render_template('questionnaire.html', title='Find my major', step=step, prompt=prompt,
                           answer=answer, error=error, completed=len(answers), total=len(QUESTIONS)), 400 if error else 200


@web.get('/questionnaire/review')
def review():
    answers = state()['answers']
    if next_step(answers) is not None:
        return redirect(url_for('web.questionnaire'))
    return render_template('review.html', title='Review your answers', questions=QUESTIONS, answers=answers)


@web.get('/questionnaire/results')
def questionnaire_results():
    answers = state()['answers']
    if next_step(answers) is not None:
        return redirect(url_for('web.questionnaire'))
    result = results(answers, repository().all(), **search_options())
    return render_template('results.html', title='Your program matches', result=result, **table_context(result['rows']))


@web.post('/questionnaire/reset')
def reset_questionnaire():
    state()['answers'] = {}
    return redirect(url_for('web.questionnaire'), code=303)


@web.get('/profile')
def profile():
    return render_template('profile.html', title='Profile')


@web.get('/settings')
def settings():
    return render_template('settings.html', title='Settings')


@web.get('/<page>.html')
def legacy_page(page):
    targets = {'index': 'web.chat', 'explore': 'web.explore', 'program-details': 'web.explore',
               'profile': 'web.profile', 'settings': 'web.settings'}
    if page not in targets:
        abort(404)
    target = 'web.questionnaire' if page == 'index' and request.args.get('mode') == 'guided' else targets[page]
    return redirect(url_for(target))


@web.get('/api/health')
def health():
    return jsonify(status='ok', engine='python', framework='flask', demo=repository().is_demo)


@web.get('/api/programs')
def programs_api():
    return jsonify(programs=repository().all(), demo=repository().is_demo)


@web.post('/api/search')
def search_api():
    if not request.is_json:
        abort(415, description='Use application/json')
    body = request.get_json()
    question = body.get('question') if isinstance(body, dict) else None
    error = validate_text(question, 12000)
    if error:
        abort(400, description=error)
    return jsonify(search(question, repository().all(), **search_options()))
