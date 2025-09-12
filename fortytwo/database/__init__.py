from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import event

from fortytwo.settings import Settings


DB_URL = Settings.DB_STRING or 'sqlite+aiosqlite:///db.sqlite3'

# For SQLite, set a connection timeout to wait for locks
connect_args = {"timeout": 30}

engine = create_async_engine(DB_URL, echo=False, connect_args=connect_args, pool_pre_ping=True)

async_session = async_sessionmaker(engine, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def on_connect(dbapi_connection, connection_record):
    """SQLite tuning: enable FKs, WAL and set busy timeout."""
    cursor = dbapi_connection.cursor()
    # Enforce foreign keys
    cursor.execute("PRAGMA foreign_keys=ON")
    # Better concurrent read/write behavior
    cursor.execute("PRAGMA journal_mode=WAL")
    # Reasonable durability with improved performance for WAL
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Wait up to N ms when the database is busy (locked)
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
