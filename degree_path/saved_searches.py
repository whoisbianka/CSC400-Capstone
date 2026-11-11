"""Translate database search records into Explore parameters."""
NUMERIC_FILTERS = ('net_price_max', 'tuition_in_max', 'tuition_out_max',
                   'acceptance_min', 'acceptance_max', 'satmt', 'satvr', 'satwr',
                   'actmt', 'acten', 'actwr')


def search_url_values(kind, row):
    values = {'view': kind, 'q': row.get('search_text') or '',
              'sort': row.get('sort_order') or ('name_asc' if kind == 'majors' else 'school_asc')}
    if kind == 'majors':
        values.update(saved=int(bool(row.get('saved'))), recs=int(bool(row.get('recs'))))
        values['majors'] = row.get('majors') or []
        values['collection_snapshot'] = 1
        if row.get('earnings_min') is not None:
            values['earnings_min'] = row['earnings_min']
    else:
        majors = row.get('majors') or []
        values.update(major_filter='selected' if majors else 'all', majors=majors,
                      school_name=row.get('colleges') or [], state=row.get('states') or [],
                      degrees=row.get('degrees') or '')
        for key in NUMERIC_FILTERS:
            if row.get(key) is not None:
                values[key] = int(row[key])
    return values
