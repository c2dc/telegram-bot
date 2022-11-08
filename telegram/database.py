from abc import ABC, abstractmethod
from typing import Any, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from .common import logger
from .connector import init_connection_engine
from .models import Channel, Message, ResumeMedia, User, UserChannel


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
    def insert_users(self, users: list) -> None:
        pass

    @abstractmethod
    def insert_users_channels(self, users_channels: list) -> None:
        pass

    @abstractmethod
    def upsert_channel(self, channel) -> None:
        pass

    @abstractmethod
    def upsert_channel_data(self, channel_id: int, data) -> None:
        pass

    @abstractmethod
    def get_channel_by_id(self, channel_id: int) -> Any:
        pass

    @abstractmethod
    def get_max_message_id(self, channel_id: int) -> Optional[int]:
        pass

    @abstractmethod
    def get_all_messages(self, channel_id: Optional[int]) -> List[str]:
        pass

    @abstractmethod
    def get_messages_with_pattern(self, pattern: str) -> List[str]:
        pass

    @abstractmethod
    def get_resume_media(self, channel_id: int) -> List[str]:
        pass

    @abstractmethod
    def get_users_message_count(self, channel_id: int) -> None:
        pass

    @abstractmethod
    def commit_changes(self) -> None:
        pass

    @abstractmethod
    def flush_changes(self) -> None:
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

    def insert_users(self, users: list) -> None:
        # Don't add duplicate users
        existing = self.session.execute(select(User.user_id)).scalars().all()
        users = [user for user in users if user.user_id not in existing]
        self.session.add_all(users)

    def insert_users_channels(self, users_channels: list) -> None:
        # Don't add duplicate relations
        existing = self.session.execute(
            select(UserChannel.channel_id, UserChannel.user_id)
        ).all()
        users_channels = [
            uc for uc in users_channels if (uc.channel_id, uc.user_id) not in existing
        ]

        self.session.add_all(users_channels)

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

    def upsert_channel_data(self, channel_id: int, data) -> None:
        pass

    def get_channel_by_id(self, channel_id: int) -> Optional[Channel]:
        statement = select(Channel).filter_by(channel_id=channel_id)

        return self.session.execute(statement).scalars().first()

    def get_max_message_id(self, channel_id: int) -> Optional[int]:
        statement = select(Channel.max_message_id).filter_by(channel_id=channel_id)

        return self.session.execute(statement).scalars().first()

    def get_all_messages(self, channel_id: Optional[int]) -> List[str]:
        statement = select(Message.id, Message.message, Message.message_utc).filter(
            Message.message_utc.isnot(None)
        )

        if channel_id is not None:
            statement = statement.filter_by(channel_id=channel_id)

        return self.session.execute(statement).all()

    def get_messages_with_pattern(self, pattern: str) -> List[str]:
        statement = (
            select(Message.message).filter(Message.message.like(pattern)).distinct()
        )

        return self.session.execute(statement).scalars().all()

    def get_resume_media(self, channel_id: int) -> List[str]:
        statement = select(ResumeMedia.data).filter_by(channel_id=channel_id)
        resume_media = self.session.execute(statement).scalars().all()

        self.session.execute(delete(ResumeMedia).filter_by(channel_id=channel_id))

        return resume_media

    def get_users_message_count(self, channel_id: int) -> None:
        users_from_channel = (
            select(User)
            .join(UserChannel)
            .filter_by(channel_id=channel_id)
            .cte(name="users_from_channel")
        )
        user_alias = aliased(users_from_channel)

        messages_from_channel = (
            select(Message)
            .filter_by(channel_id=channel_id)
            .cte(name="messages_from_channel")
        )
        message_alias = aliased(messages_from_channel)

        statement = (
            select(
                user_alias.c.user_id,
                user_alias.c.username,
                user_alias.c.first_name,
                user_alias.c.last_name,
                func.count(message_alias.c.message),
            )
            .join(
                user_alias,
                user_alias.c.user_id == message_alias.c.from_id,
                # full outer join to return even users without any messages
                full=True,
            )
            .group_by(
                user_alias.c.user_id,
                user_alias.c.username,
                user_alias.c.first_name,
                user_alias.c.last_name,
            )
        )

        return self.session.execute(statement).all()

    def commit_changes(self) -> None:
        try:
            self.session.commit()
        except Exception as e:
            logger.error(f"Failed to commit. Error: {e}.")
            self.session.rollback()
            raise e

    def flush_changes(self) -> None:
        try:
            self.session.flush()
        except Exception as e:
            logger.error(f"Failed to flush. Error: {e}.")
            self.session.rollback()
            raise e
