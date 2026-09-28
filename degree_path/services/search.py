"""Deterministic demo matching; no database, AI, or external services."""
import re

STATES = ('Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming').split('|')


def normalize(text):
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', text.lower()).split())


def contains(text, phrase):
    return f' {normalize(phrase)} ' in f' {text} '


def search(question, programs):
    text = normalize(question)
    vocabulary = dict.fromkeys(normalize(v) for p in programs for v in [p['major'], *p['keywords'], *p['careers']])
    terms = [term for term in vocabulary if contains(text, term)]
    terms = [term for term in terms if not any(other != term and contains(other, term) for other in terms)]
    colleges = [name for name in dict.fromkeys(p['college'] for p in programs) if contains(text, name)]
    locations = [state for state in STATES if contains(text, state)]
    locations = [state for state in locations if not any(other != state and state in other for other in locations)]
    for p in programs:
        if p['stateCode'] and re.search(r'\b' + re.escape(p['stateCode']) + r'\b', question) and p['state'] not in locations:
            locations.append(p['state'])
    cost = re.search(r'(under|below|less than|up to|at most)\s*\$?([0-9][0-9,]*(?:\.[0-9]+)?)\s*(k|thousand)?', question, re.I)
    budget = float(cost[2].replace(',', '')) * (1000 if cost[3] else 1) if cost else None
    inclusive = bool(cost and cost[1].lower() in ('up to', 'at most'))
    formats = [f for f in ['Online', 'Campus', 'Hybrid'] if contains(text, f)]
    types = [t for t in ['Public', 'Private'] if contains(text, t)]
    filters = locations + formats + types
    if budget is not None:
        amount = f'{budget:,.3f}'.rstrip('0').rstrip('.')
        filters.append(f'{"At most" if inclusive else "Under"} ${amount} annual demo tuition')
    browse = re.search(r'\b(all|any|show|list|browse)\b', text) and re.search(r'\b(programs|majors|colleges|options)\b', text)
    result = {'rows': [], 'terms': terms, 'filters': filters, 'demo': True, 'engine': 'python'}
    if not terms and not colleges and not filters and not browse:
        result['message'] = 'I could not match that question to the demo dataset. Try a subject such as computer science, nursing, business, or psychology.'
        return result
    for p in programs:
        matched = [t for t in terms if t in [normalize(v) for v in [p['major'], *p['keywords'], *p['careers']]]]
        tuition = p['tuition']
        if ((not terms or matched) and (not colleges or p['college'] in colleges)
                and (not locations or p['state'] in locations) and (not formats or p['format'] in formats)
                and (not types or p['type'] in types)
                and (budget is None or tuition is not None and (tuition <= budget if inclusive else tuition < budget))):
            result['rows'].append({**p, 'matched': matched})
    result['rows'].sort(key=lambda p: (-len(p['matched']), p['tuition'] if p['tuition'] is not None else float('inf')))
    count = len(result['rows'])
    result['message'] = (f'{count} demo program{"s" if count != 1 else ""} matched.' if count else
                         'No demo programs match these subjects and filters. Try removing a location, format, or tuition limit.')
    return result
