"""Read-only versions of database-branch's paging and scanning helpers.

Identifiers are restricted to public catalog tables; values use SQL parameters.
Instantiate CatalogTables with the app repository's Database instance.
"""

COLUMNS = {
    'schools': {'id', 'unitid', 'opeid6', 'instnm', 'ug12mn', 'city', 'stabbr',
                'longitude', 'latitude', 'iclevel', 'insturl'},
    'majors': {'id', 'cipcode', 'cipdesc'},
    'programs': {'id', 'program_id', 'unitid', 'cipcode', 'credlev'},
}


def positive_integer(value, name, maximum):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f'{name} must be an integer between 1 and {maximum}.')


class CatalogTables:
    def __init__(self, database):
        self.database = database

    def _table(self, table_name):
        if table_name not in COLUMNS:
            raise ValueError('Only schools, majors, and programs may be queried.')
        return 'public.' + table_name

    def get_a_page(self, page, page_count, table_name, column_to_sort, order='ASC'):
        table = self._table(table_name)
        positive_integer(page, 'page', 1000000)
        positive_integer(page_count, 'page_count', 5000)
        if column_to_sort not in COLUMNS[table_name]:
            raise ValueError('Unsupported sort column.')
        if not isinstance(order, str) or order.upper() not in ('ASC', 'DESC'):
            raise ValueError('order must be ASC or DESC.')
        return self.database.select(
            f'SELECT * FROM {table} ORDER BY {column_to_sort} {order.upper()} NULLS LAST, id ASC '
            'LIMIT :limit OFFSET :offset',
            {'limit': page_count, 'offset': (page - 1) * page_count})

    def paginate(self, table_name, last_id, batch_size=2000):
        table = self._table(table_name)
        positive_integer(batch_size, 'batch_size', 5000)
        if type(last_id) is not int or not 0 <= last_id <= 2147483647:
            raise ValueError('last_id must be a nonnegative 32-bit integer.')
        return self.database.select(
            f'SELECT * FROM {table} WHERE id > :last_id ORDER BY id ASC LIMIT :limit',
            {'last_id': last_id, 'limit': batch_size})

    def scan_entire_table(self, table_name, batch_size=5000):
        last_id = 0
        while True:
            rows = self.paginate(table_name, last_id, batch_size)
            if not rows:
                break
            yield from rows
            last_id = rows[-1]['id']
