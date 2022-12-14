from typing import List, Optional

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
    user_id = Column(BigInteger, nullable=False, unique=True)

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

    def __init__(self, user: types.User) -> None:
        self.user_id = user.id

        self.username = user.username
        self.first_name = user.first_name
        self.last_name = user.last_name
        self.phone = user.phone

        self.verified = user.verified
        self.restricted = user.restricted
        self.scam = user.scam
        self.fake = user.fake


class UserChannel(Base):
    __tablename__ = "users_channels"

    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, ForeignKey(Channel.channel_id), nullable=False)
    user_id = Column(BigInteger, ForeignKey(User.user_id), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "channel_id", name="uq_users_channels_user_id_channel_id"
        ),
    )

    def __init__(self, channel_id: int, user_id: int) -> None:
        self.channel_id = channel_id
        self.user_id = user_id


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

    def __init__(
        self,
        message: types.Message,
        channel_id: int,
    ):
        self.channel_id = channel_id
        self.message_id = message.id

        if isinstance(message.media, types.MessageMediaDocument):
            document = message.media.document
            self.media_id = document.id
            self.dc_id = document.dc_id
            self.access_hash = document.access_hash
            self.mime_type = document.mime_type
            self.size = document.size

            doc_types: List[str] = []
            for attribute in document.attributes:
                doc_type = self._match_doc_type(attribute)
                if doc_type is not None:
                    doc_types.append(doc_type)
            self.type = ",".join([type for type in doc_types if type is not None])

            self.message_utc = document.date
        elif isinstance(message.media, types.MessageMediaPhoto):
            photo = message.media.photo
            self.media_id = photo.id
            self.dc_id = photo.dc_id
            self.access_hash = photo.access_hash

            for size in photo.sizes:
                if isinstance(size, types.PhotoSize):
                    self.size = size.size

            self.message_utc = photo.date

    def _match_doc_type(self, attribute) -> Optional[str]:
        match attribute:
            case types.DocumentAttributeImageSize():
                return "image"
            case types.DocumentAttributeAnimated():
                return "gif"
            case types.DocumentAttributeVideo():
                return "video"
            case types.DocumentAttributeAudio():
                return "audio"
            case types.DocumentAttributeFilename():
                return "document"
            case _:
                return None


class ResumeMedia(Base):
    __tablename__ = "resume_media"

    id = Column(Integer, primary_key=True)
    channel_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    data = Column(JSONB, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            [channel_id, message_id], [Message.channel_id, Message.message_id]
        ),
    )

    def __init__(
        self,
        message: types.Message,
        channel_id: int,
    ):
        self.channel_id = channel_id
        self.message_id = message.id
        self.data = message.to_json()
