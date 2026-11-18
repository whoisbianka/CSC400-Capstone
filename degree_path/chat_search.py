"""Validate chat search intent and build internal Explore links, without program queries."""
from flask import url_for
from .chat_schemas import ExploreSearch

STATES = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY AS GU MP PR VI FM MH PW".split())


def build_search_metadata(search, db):
    if search is None:
        return {}
    search = ExploreSearch.model_validate(search)
    states = sorted(set(value.upper() for value in search.states))
    if not set(states) <= STATES:
        raise ValueError("Please use valid US states or territories for the search.")
    if any(not value or len(value) > 200 for value in search.majors + search.major_subjects + search.colleges):
        raise ValueError("Please use major and college names of 1–200 characters.")
    codes = []
    labels = []
    terms = [(name, False) for name in search.majors] + [(name, True) for name in search.major_subjects]
    for name, broad in terms:
        normalized = name.rstrip('.').casefold()
        broad = broad or normalized in ('math', 'maths', 'mathematics')
        suggestions = db.get_chat_major_matches(name)
        exact = [row for row in suggestions if row['name'].rstrip('.').casefold() == normalized]
        matches = suggestions if broad else (exact or suggestions)
        if not matches:
            raise ValueError("No catalog majors matched " + name + ". Try another subject or browse Explore majors.")
        codes.extend(str(row['cipcode']) for row in matches)
        if broad or len(matches) > 1:
            labels.append(f"{name} ({len(matches)} matching majors)")
        else:
            labels.append(matches[0]['name'])
    if len(set(codes)) > 200:
        raise ValueError("That search includes more than 200 majors. Please narrow the subject areas.")
    filters = {'view': 'programs', 'major_filter': 'selected' if codes else 'all',
               'majors': sorted(set(codes)), 'state': states,
               'school_name': sorted(set(search.colleges)),
               'degrees': ','.join(sorted({'associate': '2', 'bachelor': '3'}[v] for v in set(search.degree_levels)))}
    for key in ('school_size', 'net_price_max', 'tuition_in_max', 'tuition_out_max'):
        value = getattr(search, key)
        if value is not None:
            filters[key] = value
    summary = labels + states + search.degree_levels
    if search.school_size:
        summary.append(search.school_size + ' colleges')
    summary += search.colleges
    for key, label in [('net_price_max', 'Annual net price'), ('tuition_in_max', 'In-state tuition'), ('tuition_out_max', 'Out-of-state tuition')]:
        if getattr(search, key) is not None:
            summary.append(f"{label} up to ${getattr(search, key):,}")
    return {'explore_search': {'version': 1, 'label': 'Explore matching programs',
            'summary': ' · '.join(summary) or 'All college programs',
            'filters': filters, 'request': search.model_dump()}}


def search_card(metadata):
    search = (metadata or {}).get('explore_search')
    if not isinstance(search, dict) or search.get('version') != 1:
        return None
    allowed = {'view', 'major_filter', 'majors', 'state', 'school_name', 'degrees',
               'school_size', 'net_price_max', 'tuition_in_max', 'tuition_out_max'}
    filters = {key: value for key, value in search.get('filters', {}).items() if key in allowed}
    filters['view'] = 'programs'
    return {'label': search['label'], 'summary': search['summary'],
            'url': url_for('web.explore', **filters)}
