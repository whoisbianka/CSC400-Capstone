"""Server-side catalog filtering and sorting shared by Explore and results."""
SORTS = {'college': 'College', 'major': 'Major', 'state': 'Location', 'tuition': 'Annual tuition'}
FORMATS = ('Campus', 'Hybrid', 'Online')


def filter_programs(programs, args):
    query = args.get('q', '').strip().lower()[:2000]
    study_format = args.get('format', '')
    sort = args.get('sort', 'college')
    if sort not in SORTS:
        sort = 'college'
    descending = args.get('direction') == 'desc'
    rows = [p for p in programs if (not study_format or p['format'] == study_format)
            and (not query or query in ' '.join(str(p.get(k, '')) for k in ('college', 'major', 'state', 'type', 'format')).lower())]
    available = [p for p in rows if p.get(sort) is not None]
    missing = [p for p in rows if p.get(sort) is None]
    available.sort(key=lambda p: p[sort] if sort == 'tuition' else p[sort].casefold(), reverse=descending)
    return available + missing
