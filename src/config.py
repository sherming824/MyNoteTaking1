from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


def database_options(raw_url, *, cloud=False):
    """Normalize a Neon URL without losing its SSL options or exposing credentials."""
    try:
        url = make_url(raw_url)
    except Exception:
        raise RuntimeError('DATABASE_URL is invalid.') from None
    if url.drivername in ('postgres', 'postgresql', 'postgresql+psycopg'):
        url = url.set(drivername='postgresql+psycopg')
        if url.query.get('sslmode') not in ('require', 'verify-ca', 'verify-full'):
            url = url.update_query_dict({'sslmode': 'require'})
        return url, {'poolclass': NullPool, 'connect_args': {'connect_timeout': 10}}, False
    if url.drivername == 'sqlite' and not cloud:
        return url, {}, True
    raise RuntimeError('Configure a PostgreSQL DATABASE_URL for cloud deployment; local SQLite is not persistent on Vercel.')
