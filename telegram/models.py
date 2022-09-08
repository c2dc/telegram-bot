from sqlalchemy import (
    Column,
    Integer,
    Text,
    Boolean,
    BigInteger,
    ForeignKey,
    UniqueConstraint,
    TIMESTAMP,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

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
        self.channel_id = channel_id
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

    retrieved_utc = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_utc = Column(
        TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "message_id", "channel_id", name="uq_messages_message_id_channel_id"
        ),
    )

    def __init__(self, message_id: int, channel_id: int, data):
        self.message_id = message_id
        self.channel_id = channel_id
        self.data = data
