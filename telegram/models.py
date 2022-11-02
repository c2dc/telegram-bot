from typing import Optional

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from telethon import types

Base = declarative_base()


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, nullable=False, unique=True)
    name = Column(Text, nullable=False)
    max_message_id = Column(Integer, nullable=False)

    is_active = Column(Boolean, nullable=False, server_default="TRUE")
    is_complete = Column(Boolean, nullable=False, server_default="FALSE")

    retrieved_utc = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_utc = Column(
        TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __init__(
        self,
        channel_id: int,
        name: str,
        max_message_id: int = 0,
        is_active: bool = True,
        is_complete: bool = False,
    ):
        self.channel_id = int(channel_id)
        self.name = name
        self.max_message_id = max_message_id

        self.is_active = is_active
        self.is_complete = is_complete


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    message_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, ForeignKey(Channel.channel_id), nullable=False)
    data = Column(JSONB, nullable=False)
    message = Column(Text, nullable=True)
    views = Column(BigInteger, nullable=True)
    forwards = Column(BigInteger, nullable=True)

    from_id = Column(BigInteger, nullable=True)
    post_author = Column(Text, nullable=True)

    fwd_from_id = Column(BigInteger, nullable=True)
    fwd_from_name = Column(Text, nullable=True)
    fwd_post_author = Column(Text, nullable=True)

    message_utc = Column(TIMESTAMP, nullable=True)  # nullable because of old entries
    retrieved_utc = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_utc = Column(
        TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "message_id", "channel_id", name="uq_messages_message_id_channel_id"
        ),
    )

    def __init__(
        self,
        message: types.Message,
        channel_id: int,
    ):
        self.message_id = message.id
        self.channel_id = int(channel_id)
        self.data = message.to_json()
        self.message = message.message
        self.views = message.views
        self.forwards = message.forwards

        self.from_id = self._match_peer_id(message.from_id)
        self.post_author = message.post_author

        if message.fwd_from:
            self.fwd_from_id = self._match_peer_id(message.fwd_from.from_id)
            self.fwd_from_name = message.fwd_from.from_name
            self.fwd_post_author = message.fwd_from.post_author

        if message.entities:
            for entity in message.entities:
                match entity:
                    case types.MessageEntityUrl:
                        pass
                    case types.MessageEntityTextUrl:
                        pass
                    case _:
                        pass

        self.message_utc = message.date

    def _match_peer_id(self, peer_id) -> Optional[int]:
        match peer_id:
            case types.PeerChannel():
                return peer_id.channel_id
            case types.PeerUser():
                return peer_id.user_id
            case types.PeerChat():
                return peer_id.chat_id
            case _:
                return None


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)

    username = Column(Text, nullable=True)
    first_name = Column(Text, nullable=True)
    last_name = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)

    verified = Column(Boolean, nullable=True)
    restricted = Column(Boolean, nullable=True)
    scam = Column(Boolean, nullable=True)
    fake = Column(Boolean, nullable=True)

    retrieved_utc = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_utc = Column(
        TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Media(Base):
    __tablename__ = "media"

    id = Column(Integer, primary_key=True)
    media_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    dc_id = Column(Integer, nullable=True)
    access_hash = Column(BigInteger, nullable=True)

    mime_type = Column(Text, nullable=True)
    type = Column(Text, nullable=True)
    size = Column(Integer, nullable=True)

    message_utc = Column(TIMESTAMP, nullable=False)
    retrieved_utc = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_utc = Column(
        TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        ForeignKeyConstraint(
            [channel_id, message_id], [Message.channel_id, Message.message_id]
        ),
    )
