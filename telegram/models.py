from sqlalchemy import (
    Column,
    Integer,
    Text,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Channels(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    retrieved_utc = Column(Integer, nullable=False)
    updated_utc = Column(Integer, nullable=False)
    min_message_id = Column(Integer, nullable=False)
    max_message_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="TRUE")
    is_complete = Column(Boolean, nullable=False, server_default="FALSE")


class Messages(Base):
    __table__name = "messages"

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, nullable=False)
    channel_id = Column(Integer, nullable=False)
    retrieved_utc = Column(Integer, nullable=False)
    updated_utc = Column(Integer, nullable=False)
    data = Column(JSONB, nullable=False)
