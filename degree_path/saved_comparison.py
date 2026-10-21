"""Saved-major comparison using prototype1's verified sessions and favorites."""
from flask import abort, jsonify
from sqlalchemy import bindparam, text
from .routes import web, database_errors, positive_arg
from .auth import get_current_user


def comparison_engine():
    import db_functions
    return db_functions.engine


def comparison_programs(connection, user_id, cipcode=None, page=1):
    """Fetch four real programs per saved major, with bounded, batched facts."""
    params = {'user_id': user_id}
    condition = ''
    if cipcode is not None:
        condition = ' AND f.cipcode = :cipcode'
        params['cipcode'] = cipcode
    majors = connection.execute(text('''SELECT m.cipcode, m.cipdesc AS name
        FROM major_fav f JOIN majors m ON m.cipcode = f.cipcode
        WHERE f.user_id = :user_id''' + condition +
        ' ORDER BY f.id DESC, m.cipcode'), params).mappings().all()
    if cipcode is not None and not majors:
        abort(404, description='Saved major not found.')
    if not majors:
        return []
    params.update(start=(page - 1) * 4, end=page * 4 + 1)
    records = connection.execute(text('''WITH ranked AS (
        SELECT p.program_id, p.unitid, p.cipcode, p.credlev,
            s.instnm AS college, s.city, s.stabbr AS state,
            ROW_NUMBER() OVER (PARTITION BY p.cipcode ORDER BY
                CASE p.credlev WHEN 3 THEN 0 WHEN 2 THEN 1 ELSE 2 END,
                s.instnm, p.program_id) AS position
        FROM programs p JOIN schools s ON s.unitid = p.unitid
        JOIN major_fav f ON f.cipcode = p.cipcode
        WHERE f.user_id = :user_id''' + condition + '''
        ) SELECT * FROM ranked WHERE position > :start AND position <= :end
        ORDER BY cipcode, position'''), params).mappings().all()
    groups = {m['cipcode']: {**dict(m), 'programs': [], 'page': page, 'has_next': False}
              for m in majors}
    visible = []
    for record in records:
        if record['position'] == params['end']:
            groups[record['cipcode']]['has_next'] = True
        else:
            visible.append(dict(record))
    if visible:
        # Pick one fact row per college/program, matching the details page's
        # first-row convention without multiplying programs when rows repeat.
        query = text('''SELECT p.program_id,
            c.npt4, c.npt43, c.tuitionfee_in, c.tuitionfee_out,
            a.adm_rate, a.satmt25, a.satmt75, a.satvr25, a.satvr75,
            a.actmt25, a.actmt75, a.acten25, a.acten75,
            r.earn_mdn_4yr_nat AS earnings
            FROM programs p
            LEFT JOIN cost_info c ON c.id = (
                SELECT MIN(id) FROM cost_info WHERE unitid = p.unitid)
            LEFT JOIN adm_crit a ON a.id = (
                SELECT MIN(id) FROM adm_crit WHERE unitid = p.unitid)
            LEFT JOIN program_rank_crit r ON r.id = (
                SELECT MIN(id) FROM program_rank_crit WHERE program_id = p.program_id)
            WHERE p.program_id IN :ids''').bindparams(bindparam('ids', expanding=True))
        facts = {row['program_id']: dict(row) for row in connection.execute(
            query, {'ids': [p['program_id'] for p in visible]}).mappings()}
        for record in visible:
            detail = facts[record['program_id']]
            detail.pop('program_id')
            for key, value in detail.items():
                # Suppressed and missing amounts are not zero-dollar programs.
                if value is not None:
                    detail[key] = float(value) if key == 'adm_rate' else int(value)
                    if detail[key] < 0 or (key == 'adm_rate' and detail[key] > 1):
                        detail[key] = None
            record.pop('position')
            record.update(detail)
            record['major'] = groups[record['cipcode']]['name']
            groups[record['cipcode']]['programs'].append(record)
    return list(groups.values())


def require_comparison_user():
    user = get_current_user()
    if user is None:
        abort(401, description='Sign in to compare your saved majors.')
    return user['id']


@web.get('/api/saved-majors/programs')
@database_errors
def saved_comparison_api():
    user_id = require_comparison_user()
    with comparison_engine().connect() as connection:
        return jsonify(majors=comparison_programs(connection, user_id))


@web.get('/api/saved-majors/<int:cipcode>/programs')
@database_errors
def saved_major_programs_api(cipcode):
    user_id = require_comparison_user()
    page = positive_arg('page', 1, 100000)
    with comparison_engine().connect() as connection:
        return jsonify(comparison_programs(connection, user_id, cipcode, page)[0])
