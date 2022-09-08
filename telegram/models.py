import time

from sqlalchemy import (
    Column,
    Integer,
    Text,
    Boolean,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, nullable=False)
    name = Column(Text, nullable=False)
    retrieved_utc = Column(Integer, nullable=False)
    updated_utc = Column(Integer, nullable=False)
    min_message_id = Column(Integer, nullable=False)
    max_message_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="TRUE")
    is_complete = Column(Boolean, nullable=False, server_default="FALSE")

    def __init__(
        self,
        channel_id: int,
        name: str,
        min_message_id: int,
        max_message_id: int,
        is_active: bool = True,
        is_complete: bool = False,
    ):
        self.channel_id = channel_id
        self.name = name
        self.min_message_id = min_message_id
        self.max_message_id = max_message_id
        self.is_active = is_active
        self.is_complete = is_complete

        self.retrieved_utc = int(time.time())
        self.updated_utc = int(time.time())


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, nullable=False)
    channel_id = Column(Integer, nullable=False)
    retrieved_utc = Column(Integer, nullable=False)
    updated_utc = Column(Integer, nullable=False)
    data = Column(JSONB, nullable=False)

    def __init__(self, message_id: int, channel_id: int, data):
        self.message_id = message_id
        self.channel_id = channel_id
        self.data = data

        self.retrieved_utc = int(time.time())
        self.updated_utc = int(time.time())
