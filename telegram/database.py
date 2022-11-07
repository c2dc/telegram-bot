from abc import ABC, abstractmethod
from typing import Any, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .common import logger
from .connector import init_connection_engine
from .models import Channel, Message, ResumeMedia


class Database(ABC):
    def __init__(self):
        pass

    def __enter__(self):
        return self

    @abstractmethod
    def insert_messages(self, messages: list) -> None:
        pass

    @abstractmethod
    def insert_media(self, media: list) -> None:
        pass

    @abstractmethod
    def insert_resume_media(self, resume_media: list) -> None:
        pass

    @abstractmethod
    def upsert_channel(self, channel) -> None:
        pass

    @abstractmethod
    def upsert_channel_data(self, channel_id, data) -> None:
        pass

    @abstractmethod
    def get_channel_by_id(self, channel_id) -> Any:
        pass

    @abstractmethod
    def get_max_message_id(self, channel_id) -> Optional[int]:
        pass

    @abstractmethod
    def get_messages_with_pattern(self, pattern: str) -> List[str]:
        pass

    @abstractmethod
    def get_resume_media(self, channel_id) -> List[str]:
        pass

    @abstractmethod
    def commit_changes(self) -> None:
        pass


class PgDatabase(Database):
    def __init__(self):
        pool = init_connection_engine(method="tcp")

        self.session = Session(pool)
        self.session.begin()

    def insert_messages(self, messages: list) -> None:
        self.session.add_all(messages)

    def insert_media(self, media: list) -> None:
        self.session.add_all(media)

    def insert_resume_media(self, resume_media: list) -> None:
        self.session.add_all(resume_media)

    def upsert_channel(self, channel) -> None:
        statement = (
            insert(Channel)
            .values(
                channel_id=channel.channel_id,
                name=channel.name,
                max_message_id=channel.max_message_id,
            )
            .on_conflict_do_update(
                index_elements=["channel_id"],
                set_=dict(max_message_id=channel.max_message_id),
            )
        )

        self.session.execute(statement)

    def upsert_channel_data(self, channel_id, data) -> None:
        pass

    def get_channel_by_id(self, channel_id) -> Optional[Channel]:
        statement = select(Channel).filter_by(channel_id=channel_id)

        return self.session.execute(statement).scalars().first()

    def get_max_message_id(self, channel_id) -> Optional[int]:
        statement = select(Channel.max_message_id).filter_by(channel_id=channel_id)

        return self.session.execute(statement).scalars().first()

    def get_messages_with_pattern(self, pattern: str) -> List[str]:
        statement = (
            select(Message.message).filter(Message.message.like(pattern)).distinct()
        )

        return self.session.execute(statement).scalars().all()

    def get_resume_media(self, channel_id) -> List[str]:
        statement = select(ResumeMedia.data).filter_by(channel_id=channel_id)
        resume_media = self.session.execute(statement).scalars().all()

        self.session.execute(delete(ResumeMedia).filter_by(channel_id=channel_id))

        return resume_media

    def commit_changes(self) -> None:
        try:
            self.session.commit()
        except Exception as e:
            logger.error(f"Failed to commit. Error: {e}.")
            self.session.rollback()
