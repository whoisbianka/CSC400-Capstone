"""Validate saved Explore controls without accepting arbitrary URL parameters."""
from werkzeug.datastructures import MultiDict

PROGRAM_FIELDS = {'school_name', 'sort', 'major_filter', 'major_name', 'cipcode', 'favorite_major',
                  'degree', 'degrees', 'degree_form', 'state', 'city', 'net_price_max',
                  'tuition_in_max', 'tuition_out_max', 'acceptance_min', 'acceptance_max'}
MAJOR_FIELDS = {'q', 'sort', 'earnings_min', 'favorites_only', 'has_programs'}


def validate_explore_preferences(kind, values):
    if kind not in ('programs', 'majors') or not isinstance(values, dict):
        raise ValueError('Choose a valid Explore view and filters.')
    allowed = PROGRAM_FIELDS if kind == 'programs' else MAJOR_FIELDS
    if set(values) - allowed:
        raise ValueError('Unknown Explore filter.')
    clean = {}
    for key, items in values.items():
        if not isinstance(items, list) or len(items) > 200 or any(not isinstance(v, str) or len(v) > 200 for v in items):
            raise ValueError('Invalid filter values.')
        if key not in ('favorite_major', 'degree') and len(items) != 1:
            raise ValueError('Send one value per filter.')
        clean[key] = [v.strip() for v in items]
    args = MultiDict((k, v) for k, values in clean.items() for v in values)
    numeric = {'net_price_max': (0, 2147483647), 'tuition_in_max': (0, 2147483647),
               'tuition_out_max': (0, 2147483647), 'acceptance_min': (0, 100),
               'acceptance_max': (0, 100), 'earnings_min': (0, 2147483647),
               'cipcode': (1, 2147483647), 'favorite_major': (1, 2147483647)}
    for key, (low, high) in numeric.items():
        for value in args.getlist(key):
            if value:
                try:
                    number = int(value)
                except ValueError:
                    raise ValueError('Numeric filters must use whole numbers.')
                if not low <= number <= high:
                    raise ValueError('Filter value is out of range.')
    if int(args.get('acceptance_min') or 0) > int(args.get('acceptance_max') or 100):
        raise ValueError('Minimum acceptance rate cannot exceed maximum.')
    sorts = ('school_asc', 'school_desc', 'earnings_desc', 'net_price_asc', 'tuition_in_asc', 'tuition_out_asc') if kind == 'programs' else ('name_asc', 'name_desc', 'earnings_desc', 'earnings_asc', 'programs_desc')
    if 'sort' in args and args['sort'] not in sorts:
        raise ValueError('Invalid sort.')
    for flag in ('favorites_only', 'has_programs'):
        if flag in args and args[flag] not in ('0', '1'):
            raise ValueError('Invalid filter flag.')
    if len(args.get('state', '')) > 3 or len(args.get('city', '')) > 100:
        raise ValueError('Invalid location.')
    degrees = args.getlist('degree') if 'degree_form' in args else args.get('degrees', '').split(',')
    if any(value not in ('', '2', '3') for value in degrees):
        raise ValueError('Invalid degree level.')
    if kind == 'programs':
        mode = args.get('major_filter', 'all')
        if mode not in ('all', 'name', 'favorites'):
            raise ValueError('Invalid major filter.')
        clean['degrees'] = [','.join(sorted(set(degrees) - {''}))]
        clean.pop('degree', None)
        clean.pop('degree_form', None)
        clean.pop('major_filter', None)
        for key in ('major_name', 'cipcode', 'favorite_major'):
            if key in clean:
                clean[key] = [value for value in clean[key] if value]
                if not clean[key]:
                    clean.pop(key)
    clean.pop('has_programs', None)  # Ignore the retired control in older saved forms.
    return clean
