from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, session, url_for
import re
import secrets
from urllib.parse import urlsplit
from functools import wraps
from werkzeug.exceptions import HTTPException
from time import perf_counter
from copy import deepcopy

import db_functions

from .auth import get_current_user, establish_login
from .preferences import validate_explore_preferences
from .guest_state import get_or_create_guest_session
from .chat_service import interpret_message, InvalidAdvisorResponse


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
def program_page(page=1, cipcode=None, degrees=None, filters=None, shuffle_seed=None, *, sort_option="school_name", sort_order="ASC"):
    import db_functions
    search_filters={**(filters or {}),
                    "cipcode":cipcode,
                    "degrees":degrees}
    try:
        data=db_functions.get_page_programs(
            page=page,
            page_count=25,
            filters=search_filters,
            sort_option=sort_option,
            sort_order=sort_order
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
    if request.method == 'POST':
        return redirect(url_for('web.chat'), code=303)
    return render_template('chat.html', title='Degree Path Assistant')


@web.post('/chat/reset')
def reset_chat():
    return redirect(url_for('web.chat'), code=303)

@web.get('/questionnaire')
def questionnaire():
    return redirect(url_for('web.chat'), code=301)

@web.get('/explore')
def explore():
    view = request.args.get('view', 'programs')
    if view not in ('programs', 'majors'):
        abort(400, description='Choose Programs or Majors.')
    restored = restore_explore_preferences(view)
    if restored is not None:
        return restored
    if view == 'majors':
        return explore_major_catalog()
    sort = request.args.get('sort', 'school_asc')
    sorts = {'school_asc': ('school_name', 'ASC'), 'school_desc': ('school_name', 'DESC'),
             'earnings_desc': ('earnings', 'DESC'), 'net_price_asc': ('npt4', 'ASC'),
             'tuition_in_asc': ('tuitionfee_in', 'ASC'), 'tuition_out_asc': ('tuitionfee_out', 'ASC')}
    if sort not in sorts:
        abort(400, description='Invalid program sort.')
    page = positive_arg('page', 1, 100000)
    cipcode = positive_arg('cipcode')
    major_query = request.args.get('major_name', '').strip()
    major_filter = request.args.get('major_filter', 'name' if cipcode or major_query else 'all')
    if major_filter not in ('all', 'name', 'favorites'):
        abort(400, description='Invalid major filter.')
    if len(major_query) > 200:
        abort(400, description='Major names must be at most 200 characters.')
    favorite_majors = []
    if session.get('user_id'):
        try:
            favorite_majors = db_functions.get_major_favorites(session['user_id'])
        except Exception:
            current_app.logger.exception('Unable to load favorite major filters.')
            abort(503, description='Unable to load favorite majors. Please retry.')
    selected_favorites = []
    major_filters = {}
    if request.args.getlist('favorite_major'):
        if not session.get('user_id'):
            return redirect(url_for('web.favorites'))
        try:
            selected_favorites = sorted({int(value) for value in request.args.getlist('favorite_major')})
        except ValueError:
            abort(400, description='Invalid favorite major selection.')
        allowed = {row['cipcode'] for row in favorite_majors}
        if not set(selected_favorites) <= allowed:
            abort(400, description='A selected major is no longer in your favorites. Reset the filters and try again.')
        major_filters['cipcodes'] = selected_favorites
    if major_query:
        major_filters['major_name'] = major_query
        cipcode = None
    major_filter = 'name' if major_query or cipcode else ('favorites' if selected_favorites else 'all')
    # No selected degrees means no degree restriction.
    degree_values = (request.args.getlist('degree') if 'degree_form' in request.args
                     else request.args.get('degrees', '').split(','))
    if any(value not in ('', '2', '3') for value in degree_values):
        abort(400, description='Invalid degree level.')
    degrees = tuple(sorted({int(value) for value in degree_values if value}))
    filters = {}
    school_query = request.args.get('school_name', '').strip()
    if len(school_query) > 200:
        abort(400, description='School names must be at most 200 characters.')
    if school_query:
        filters['school_name'] = school_query
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
    data = program_page(page, cipcode, degrees, {**filters, **major_filters}, session['explore_shuffle_seed'],
                        sort_option=sorts[sort][0], sort_order=sorts[sort][1])
    major_name=None
    if cipcode is not None and data["rows"]:
        major_name=data["rows"][0]["major"]
    if cipcode and major_name:
        major_query = major_name
    pagination = {**filters, 'preferences_applied': '1', 'view': 'programs', 'sort': sort, 'degrees': ','.join(map(str, degrees)),
                  'major_filter': major_filter}
    if major_filter == 'name':
        pagination.update(major_name=major_query, cipcode=cipcode)
    if selected_favorites:
        pagination['favorite_major'] = selected_favorites
    return render_template('explore.html', title='Explore programs', data=data,
                           major_name=major_name, cipcode=cipcode, degrees=degrees,
                           degree_query=','.join(map(str, degrees)), filters=filters,
                           major_filter=major_filter, major_query=major_query,
                           favorite_majors=favorite_majors, selected_favorites=selected_favorites,
                           pagination=pagination, explore_view='programs', program_sort=sort)

@web.get('/majors/<int:cipcode>')
def major_details(cipcode):
    if not 1 <= cipcode <= 2147483647:
        abort(404, description='Major not found.')
    try:
        major = db_functions.get_major_details(cipcode, session.get('user_id'))
    except Exception:
        current_app.logger.exception('Unable to load major details.')
        abort(503, description='Major details are unavailable. Please retry.')
    if major is None:
        abort(404, description='Major not found.')
    try:
        recommendations = []
        if session.get('user_id'):
            recommendations = db_functions.get_recommendations(session['user_id'])
        elif isinstance(session.get('guest_id'), str):
            guest = db_functions.get_guest_session(session['guest_id'])
            if guest is not None:
                recommendations = guest['state'].get('recommendations', [])
        recommendation = next((item for item in recommendations
                               if item['cipcode'] == cipcode), None)
    except Exception:
        current_app.logger.exception('Unable to load matching interests.')
        abort(503, description='Matching interests are unavailable. Please retry.')
    return render_template('major_details.html', title=major['major'], major=major,
                           recommendation=recommendation)


@web.get('/programs/<int:program_id>')
def program_details(program_id):
    details = program(program_id)
    if details is None:
        abort(404, description='Program not found.')
    return render_template('program_details.html', title=details['major'], program=details)

@web.get('/start/<destination>')
def start(destination):
    # Keep old bookmarks working without the account-choice screen.
    endpoints = {'questionnaire': 'web.chat', 'chat': 'web.chat', 'explore': 'web.explore'}
    if destination not in endpoints:
        abort(404)
    return redirect(url_for(endpoints[destination]))


@web.get('/profile')
def profile():
    return render_template('profile.html', title='Profile')


@web.get('/settings')
def settings():
    return render_template('settings.html', title='Settings')


@web.get('/<page>.html')
def legacy_page(page):
    targets = {'index': 'web.home', 'chatbot': 'web.chat',
               'explore': 'web.explore', 'program-details': 'web.explore',
               'profile': 'web.profile', 'settings': 'web.settings'}
    if page not in targets:
        abort(404)
    target = 'web.chat' if page == 'index' and request.args.get('mode') == 'guided' else targets[page]
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

@web.route("/api/chat", methods=["GET", "POST"])
def api_chat():
    message = None

    if request.method == "POST":
        body = request.get_json(silent=True)

        if not isinstance(body, dict):
            abort(400, description="Send a JSON object.")

        message = body.get("message")

        if not isinstance(message, str):
            abort(400, description="A message is required.")

        message = message.strip()

        if not 1 <= len(message) <= 4000:
            abort(
                400,
                description="Messages must contain 1–4000 characters.",
            )

    try:
        user = get_current_user()

        if user is not None:
            mode = "user"
            user_id = user["id"]

            messages = db_functions.get_recent_chatlog(user_id)
            keywords = db_functions.get_user_keywords(user_id)

        else:
            mode = "guest"
            guest_id, guest = get_or_create_guest_session()

            messages = guest["state"]["messages"]
            keywords = guest["state"]["keywords"]

        if request.method == "GET":
            if user is not None:
                major_recommendations = db_functions.get_recommendations(
                    user_id
                )
            else:
                major_recommendations = guest["state"].get(
                    "recommendations",
                    [],
                )

            return jsonify(
                mode=mode,
                messages=messages,
                keywords=keywords,
                recommendations=major_recommendations,
            )

        catalog = db_functions.get_keywords()

        turn = interpret_message(
            message=message,
            keyword_catalog=catalog,
            saved_keywords=keywords,
            recent_messages=messages[-20:],
        )

        if user is not None:
            major_recommendations = db_functions.save_chat_turn(
                user_id,
                message,
                turn,
            )

        else:
            updated_state = apply_guest_chat_turn(
                state=guest["state"],
                message=message,
                turn=turn,
                catalog=catalog,
            )

            major_recommendations = (
                db_functions.get_recommendations_for_keywords(
                    updated_state["keywords"]
                )
            )

            updated_state["recommendations"] = major_recommendations

            new_version = db_functions.save_guest_session(
                guest_id=guest_id,
                state=updated_state,
                expected_version=guest["version"],
            )

            if new_version is None:
                abort(
                    409,
                    description=(
                        "This chat changed in another tab or expired. "
                        "Reload the chat before sending again."
                    ),
                )

        return jsonify(
            mode=mode,
            reply=turn.reply,
            recommendations=major_recommendations,
        )

    except HTTPException:
        raise

    except InvalidAdvisorResponse:
        current_app.logger.exception(
            "Gemini returned an invalid chat response."
        )
        abort(
            502,
            description="The assistant could not respond. Please try again.",
        )

    except Exception:
        current_app.logger.exception("Chat request failed.")
        abort(
            503,
            description="Chat is temporarily unavailable. Please try again.",
        )


def apply_guest_chat_turn(state, message, turn, catalog):
    updated = deepcopy(state)

    keywords_by_id = {
        item["keyword_id"]: item
        for item in updated["keywords"]
    }

    labels_by_id = {
        item["keyword_id"]: item["keyword"]
        for item in catalog
    }

    for keyword_id in turn.keyword_removals:
        keywords_by_id.pop(keyword_id, None)

    for addition in turn.keyword_additions:
        keywords_by_id[addition.keyword_id] = {
            "keyword_id": addition.keyword_id,
            "keyword": labels_by_id[addition.keyword_id],
            "evidence": addition.evidence,
        }

    updated["keywords"] = list(keywords_by_id.values())

    updated["messages"].extend([
        {"role": "user", "content": message},
        {"role": "assistant", "content": turn.reply},
    ])

    # Keep guest state bounded.
    updated["messages"] = updated["messages"][-100:]

    # Existing recommendations may no longer match changed interests.
    if turn.keyword_additions or turn.keyword_removals:
        updated["recommendations"] = []

    return updated


@web.get("/favorites")
def favorites():
    return render_template(
        "favorites.html",
        title="Favorites",
    )


@web.route("/api/favorites", methods=["GET", "POST"])
def favorites_api():
    try:
        user = get_current_user()

        if user is None:
            abort(
                401,
                description="Sign in to save and view favorite majors.",
            )

        # Always use the identity verified by Clerk.
        user_id = user["id"]

        if request.method == "GET":
            if request.args.get("details") == "1":
                rows = db_functions.get_comparison_favorites(user_id, "majors")
                return jsonify(favorites=[{**row, "cipcode": row["id"], "major": row["name"]} for row in rows])
            return jsonify(favorites=db_functions.get_major_favorites(user_id))

        body = request.get_json(silent=True)

        if not isinstance(body, dict):
            abort(400, description="Send a JSON object.")

        cipcode = body.get("cipcode")
        favorite = body.get("favorite")

        if type(cipcode) is not int or not 0 < cipcode <= 2147483647:
            abort(400, description="A valid major code is required.")

        if type(favorite) is not bool:
            abort(400, description="favorite must be true or false.")

        if favorite:
            exists = db_functions.add_major_fav(user_id, cipcode)

            if not exists:
                abort(404, description="This major does not exist.")
        else:
            db_functions.remove_from_major_fav(user_id, cipcode)

        return jsonify(
            cipcode=cipcode,
            favorite=favorite,
        )

    except HTTPException:
        raise

    except Exception:
        current_app.logger.exception("Favorites request failed.")
        abort(
            503,
            description="Favorites are temporarily unavailable. Try again.",
        )

@web.post("/api/auth/session")
def auth_session_api():
    try:
        user = establish_login()
        return jsonify(user_id=user["id"])
    except HTTPException:
        raise
    except Exception:
        current_app.logger.exception("Unable to establish login session.")
        abort(503, description="Unable to sign in right now. Please try again.")


@web.post("/logout")
def logout():
    # Clear Flask even if Clerk is unavailable in the browser.
    session.clear()
    return jsonify(ok=True)


@web.get("/compare")
def compare():
    return render_template("compare.html", title="Compare")


@web.get("/api/compare")
def compare_api():
    from .comparison import comparison_payload
    kind = request.args.get("kind", "majors")
    if kind not in ("majors", "programs"):
        abort(400, description="Choose majors or programs.")
    user = get_current_user()
    if user is None:
        abort(401, description="Sign in to compare your favorites.")
    try:
        rows = db_functions.get_comparison_favorites(user["id"], kind)
        return jsonify(comparison_payload(kind, rows))
    except Exception:
        current_app.logger.exception("Comparison request failed.")
        abort(503, description="Comparison data is unavailable. Please retry.")


@web.route("/api/program-favorites/<int:program_id>", methods=["GET", "POST"])
def program_favorite_api(program_id):
    if not 0 < program_id <= 2147483647:
        abort(400, description="Invalid program ID.")
    user = get_current_user()
    if user is None:
        abort(401, description="Sign in to save programs.")
    try:
        if request.method == "GET":
            favorite = db_functions.is_program_favorite(user["id"], program_id)
        else:
            body = request.get_json(silent=True)
            if not isinstance(body, dict) or type(body.get("favorite")) is not bool:
                abort(400, description="favorite must be true or false.")
            favorite = body["favorite"]
            if favorite:
                if not db_functions.add_program_fav(user["id"], program_id):
                    abort(404, description="Program not found.")
            else:
                db_functions.remove_school_fav(user["id"], program_id)
        return jsonify(program_id=program_id, favorite=favorite)
    except HTTPException:
        raise
    except Exception:
        current_app.logger.exception("Program favorite request failed.")
        abort(503, description="Unable to update program favorites. Please retry.")


@web.get("/api/program-favorites")
def program_favorites_api():
    from .comparison import CREDENTIALS
    user = get_current_user()
    if user is None:
        abort(401, description="Sign in to view your favorite programs.")
    try:
        if request.args.get("details") == "1":
            rows = db_functions.get_comparison_favorites(user["id"], "programs")
            favorites = [{**row, "program_id": row["id"], "major": row["name"]} for row in rows]
        else:
            favorites = db_functions.get_program_favorites(user["id"])
        for favorite in favorites:
            favorite["credential"] = CREDENTIALS.get(favorite.get("credlev"), "Not reported")
            favorite["url"] = url_for("web.program_details", program_id=favorite["program_id"])
        return jsonify(favorites=favorites)
    except Exception:
        current_app.logger.exception("Unable to load program favorites.")
        abort(503, description="Program favorites are unavailable. Please retry.")


@web.get("/api/major-names")
def major_names_api():
    query = request.args.get("q", "").strip()
    if len(query) > 200:
        abort(400, description="Major names must be at most 200 characters.")
    if len(query) < 2:
        return jsonify(majors=[])
    try:
        return jsonify(majors=db_functions.get_major_name_suggestions(query))
    except Exception:
        current_app.logger.exception("Major name search failed.")
        abort(503, description="Major suggestions are unavailable. Enter an exact major name or retry.")


def explore_major_catalog():
    page = positive_arg('page', 1, 100000)
    query = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'name_asc')
    favorite_flag = request.args.get('favorites_only', '0')
    if favorite_flag not in ('0', '1'):
        abort(400, description='Invalid major filter.')
    favorites_only = favorite_flag == '1'
    if favorites_only and not session.get('user_id'):
        return redirect(url_for('web.favorites'))
    raw_earnings = request.args.get('earnings_min', '').strip()
    try:
        earnings_min = int(raw_earnings) if raw_earnings else None
    except ValueError:
        abort(400, description='Minimum earnings must be a whole number.')
    try:
        data = db_functions.get_major_catalog_page(
            page, query=query, sort=sort, earnings_min=earnings_min,
            favorites_only=favorites_only,
            user_id=session.get('user_id'),
        )
    except ValueError as error:
        abort(400, description=str(error))
    except Exception:
        current_app.logger.exception('Unable to load major catalog.')
        abort(503, description='The major catalog is unavailable. Please retry.')
    pagination = {'preferences_applied': '1', 'view': 'majors', 'q': query, 'sort': sort,
                  'earnings_min': earnings_min, 'favorites_only': int(favorites_only)}
    return render_template('explore_majors.html', title='Explore majors', explore_view='majors',
                           data=data, query=query, sort=sort, earnings_min=earnings_min,
                           favorites_only=favorites_only,
                           pagination=pagination)



def saved_explore_preferences(user):
    if user is not None:
        saved = session.get('explore_preferences', {})
        views = deepcopy(saved.get('views', {})) if saved.get('user_id') == user['id'] else {}
        views['programs'] = {**views.get('programs', {}), **db_functions.get_program_preferences(user['id'])}
        return views
    guest_id = session.get('guest_id')
    guest = db_functions.get_guest_session(guest_id) if guest_id else None
    return guest['state'].get('explore_preferences', {}) if guest else {}


def restore_explore_preferences(view):
    # Explicit searches, pagination and resets must not silently reapply defaults.
    if set(request.args) - {'view', 'cipcode', 'major_name'}:
        return None
    try:
        user = get_current_user()
        saved = deepcopy(saved_explore_preferences(user).get(view, {}))
        # Missing values must not become the strings 'None' or 'null' in filters.
        saved = {key: values for key, values in saved.items()
                 if isinstance(values, list) and values and all(isinstance(v, str) for v in values)}
        if not any(any(value for value in values) for values in saved.values()):
            return None
        if 'cipcode' in request.args or 'major_name' in request.args:
            for key in ('favorite_major', 'major_name', 'cipcode', 'major_filter'):
                saved.pop(key, None)
            for key in ('cipcode', 'major_name'):
                if key in request.args:
                    saved[key] = [request.args[key]]
        # A favorite removed since saving is no longer a valid selection.
        saved.pop('major_filter', None)
        saved.pop('has_programs', None)
        if saved.get('favorite_major') and user:
            allowed = {str(row['cipcode']) for row in db_functions.get_major_favorites(user['id'])}
            saved['favorite_major'] = [code for code in saved.get('favorite_major', []) if code in allowed]
        return redirect(url_for('web.explore', view=view, preferences_applied='1', **saved))
    except HTTPException:
        raise
    except Exception:
        current_app.logger.exception('Unable to restore optional Explore preferences; using visible filters.')
        return None


@web.post('/api/explore/preferences')
def explore_preferences_api():
    user = get_current_user()
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or body.get('action') not in ('save', 'reset'):
        abort(400, description='Choose save or reset.')
    kind = body.get('view', 'programs')
    if kind not in ('programs', 'majors'):
        abort(400, description='Choose programs or majors.')
    try:
        values = validate_explore_preferences(kind, body.get('filters', {})) if body['action'] == 'save' else {}
    except ValueError as error:
        abort(400, description=str(error))
    try:
        if values.get('favorite_major') or values.get('favorites_only') == ['1']:
            if user is None:
                abort(401, description='Sign in to use favorite filters.')
            allowed = {str(row['cipcode']) for row in db_functions.get_major_favorites(user['id'])}
            if not set(values.get('favorite_major', [])) <= allowed:
                abort(400, description='A selected major is no longer a favorite.')
        if user is not None:
            if body['action'] == 'reset':
                db_functions.reset_user_preferences(user['id'])
                session.pop('explore_preferences', None)
                session.pop('program_degree', None)
            else:
                if kind == 'programs':
                    db_functions.save_program_preferences(user['id'], values)
                saved = session.get('explore_preferences', {})
                views = deepcopy(saved.get('views', {})) if saved.get('user_id') == user['id'] else {}
                views[kind] = values
                session['explore_preferences'] = {'user_id': user['id'], 'views': views}
        else:
            guest_id, guest = get_or_create_guest_session()
            state = deepcopy(guest['state'])
            if body['action'] == 'reset':
                state['explore_preferences'] = {}
                state['preferences'] = {}
            else:
                state.setdefault('explore_preferences', {})[kind] = values
            if db_functions.save_guest_session(guest_id, state, guest['version']) is None:
                abort(409, description='Your session changed. Reload and try again.')
        return jsonify(ok=True, url=url_for('web.explore', view=kind, preferences_applied='1', **values))
    except HTTPException:
        raise
    except Exception:
        current_app.logger.exception('Unable to save Explore preferences.')
        abort(503, description='Preferences could not be updated. Please retry.')


@web.post('/api/chat/reset')
def reset_advisor_chat_api():
    user = get_current_user()
    try:
        if user is not None:
            db_functions.reset_user_chat(user['id'])
        else:
            guest_id, guest = get_or_create_guest_session()
            state = deepcopy(guest['state'])
            state.update(messages=[], keywords=[], recommendations=[])
            if db_functions.save_guest_session(guest_id, state, guest['version']) is None:
                abort(409, description='Your chat changed. Reload before resetting.')
        return jsonify(ok=True)
    except HTTPException:
        raise
    except Exception:
        current_app.logger.exception('Unable to reset chat.')
        abort(503, description='Chat could not be reset. Please retry.')
