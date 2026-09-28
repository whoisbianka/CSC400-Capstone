"""Lazy, read-only PostgreSQL access; no schema creation or data imports."""
import atexit
import ssl
from threading import Lock


class DatabaseUnavailable(RuntimeError):
    pass


class Database:
    def __init__(self, config):
        self.config = dict(config)
        self.engine = None
        self.connector = None
        self.lock = Lock()
        atexit.register(self.close)

    def _engine(self):
        with self.lock:
            if self.engine is not None:
                return self.engine
            from sqlalchemy import URL, create_engine
            cfg = self.config
            required = ['DB_USER', 'DB_PASS', 'DB_NAME']
            required += ['INSTANCE_CONNECTION_NAME'] if cfg['PROGRAM_DATA_SOURCE'] == 'cloudsql' else ['DB_HOST']
            missing = [key for key in required if not cfg.get(key)]
            if missing:
                raise DatabaseUnavailable('Missing database settings: ' + ', '.join(missing))
            options = dict(pool_size=5, max_overflow=2, pool_timeout=10, pool_pre_ping=True, hide_parameters=True)
            if cfg['PROGRAM_DATA_SOURCE'] == 'cloudsql':
                from google.cloud.sql.connector import Connector, IPTypes
                private = str(cfg.get('PRIVATE_IP', 'false')).lower()
                if private not in ('true', 'false'):
                    raise DatabaseUnavailable('PRIVATE_IP must be true or false.')
                self.connector = Connector(refresh_strategy='LAZY', timeout=10)
                def connect():
                    return self.connector.connect(
                        cfg['INSTANCE_CONNECTION_NAME'], 'pg8000', user=cfg['DB_USER'],
                        password=cfg['DB_PASS'], db=cfg['DB_NAME'], timeout=10,
                        ip_type=IPTypes.PRIVATE if private == 'true' else IPTypes.PUBLIC,
                    )
                self.engine = create_engine('postgresql+pg8000://', creator=connect, **options)
            else:
                tls = str(cfg.get('DB_SSLMODE', 'verify-full')).lower()
                if tls not in ('disable', 'verify-full'):
                    raise DatabaseUnavailable('DB_SSLMODE must be disable or verify-full.')
                url = URL.create('postgresql+pg8000', username=cfg['DB_USER'], password=cfg['DB_PASS'],
                                 host=cfg['DB_HOST'], port=int(cfg.get('DB_PORT', 5432)), database=cfg['DB_NAME'])
                self.engine = create_engine(url, connect_args={
                    'timeout': 10, 'ssl_context': ssl.create_default_context() if tls == 'verify-full' else False,
                }, **options)
            return self.engine

    def select(self, sql, params=None):
        try:
            from sqlalchemy import text
            with self._engine().connect() as connection:
                with connection.begin():
                    connection.execute(text('SET TRANSACTION READ ONLY'))
                    connection.execute(text("SET LOCAL statement_timeout = '10s'"))
                    return list(connection.execute(text(sql), params or {}).mappings())
        except DatabaseUnavailable:
            raise
        except Exception:
            # Driver errors can contain connection strings; do not expose them to clients.
            raise DatabaseUnavailable('Database unavailable. Check your local configuration, access, and schema. Demo fallback is disabled in database mode.') from None

    def close(self):
        if self.engine is not None:
            self.engine.dispose()
            self.engine = None
        if self.connector is not None:
            self.connector.close()
            self.connector = None
