import asyncio

from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy import select
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import create_async_engine
from fortytwo.database.models import User, Message, Picture
from fortytwo.database import engine, async_session
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, delete, update, and_

async def async_main() -> None:
    #s = async_session()
    async with async_session() as s:
        #user = User(chat_id=123, username='test', title='test')
        #s.add(user)
        #await s.commit()
        #print(123)
        #print(user)
        # delete all users
        await s.execute(delete(User))
        await s.commit()


asyncio.run(async_main())