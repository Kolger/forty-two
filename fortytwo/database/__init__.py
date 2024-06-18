
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import scoped_session, sessionmaker, Session
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import event

#engine = create_async_engine(os.environ.get('DB_STRING'), echo=True)
engine = create_async_engine('sqlite+aiosqlite:///db.sqlite3', echo=True)
#s = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
#Session = sessionmaker()
#Session.configure(bind=engine)

async_session = async_sessionmaker(engine, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def enable_sqlite_fks(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()