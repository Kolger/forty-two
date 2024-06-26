from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from .utils import Common
from sqlalchemy import select, delete, update, and_

Base = declarative_base(cls=Common)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True), default=func.now())
    chat_id = Column(Integer)
    username = Column(String(255))
    title = Column(String(255))
    provider = Column(String(20), default=None)

    messages = relationship('Message', back_populates='user', cascade='all, delete-orphan')

    @classmethod
    async def get_by_chat_id(cls, chat_id, session):
        return (await session.execute(select(cls).where(cls.chat_id == chat_id))).scalar()

    async def set_provider(self, provider, session):
        await session.execute(update(User).where(self.id == User.id).values(provider=provider))

    __table_args__ = (
        UniqueConstraint('chat_id', name='uq_users_chat_id'),
    )


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True), default=func.now())
    user_id = Column(ForeignKey('users.id', ondelete='CASCADE', name='fk_user_id'))
    parent_message_id = Column(ForeignKey('messages.id', ondelete='CASCADE', name='fk_parent_message_id'))
    message_text = Column(Text)
    answer = Column(Text)
    is_active = Column(Boolean, default=True)
    completion_tokens = Column(Integer)
    prompt_tokens = Column(Integer)
    total_tokens = Column(Integer)
    is_error = Column(Boolean, default=False)
    is_ask_another_ai = Column(Boolean, default=False)

    provider = Column(String(20), default=None)

    user = relationship('User', back_populates='messages')

    # clear by user
    @classmethod
    async def clear_by_user(cls, user_id, session):
        # set is_active to False
        await session.execute(update(cls).where(cls.user_id == user_id).values(is_active=False))
        await session.commit()

    # get by user
    @classmethod
    async def get_by_user(cls, user_id, session):
        return ((await session.execute(select(cls)
                                      .where(and_(cls.user_id == user_id,
                                                  cls.is_active == True,
                                                  cls.is_error == False,
                                                  cls.is_ask_another_ai == False)))).scalars().all())

    @classmethod
    async def get_by_user_until_id(cls, user_id, session, until_id):
        return (await session.execute(select(cls)
                                      .where(and_(cls.user_id == user_id,
                                                  cls.is_active == True,
                                                  cls.is_error == False,
                                                  cls.is_ask_another_ai == False,
                                                  cls.id < until_id)))).scalars().all()


class Picture(Base):
    __tablename__ = 'pictures'

    id = Column(Integer, primary_key=True)
    message_id = Column(ForeignKey('messages.id', ondelete='CASCADE', name='fk_message_id'))
    file_base64 = Column(Text)
    media_group_id = Column(Integer)
    caption = Column(Text)

    @classmethod
    async def count_by_media_group_id(cls, media_group_id: int, session):
        pictures_count = await session.scalar(
            select(func.count(Picture.id)).where(media_group_id == cls.media_group_id)
        )

        return pictures_count