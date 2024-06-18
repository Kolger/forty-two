from sqlalchemy import Column, DateTime, func, Integer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm.exc import NoResultFound


class Common(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    date_created = Column(DateTime(timezone=True), default=func.now())
    date_updated = Column(DateTime(timezone=True), onupdate=func.now())