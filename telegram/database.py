from typing import Any, Optional
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

from .models import Channel
from .connector import init_connection_engine


class Database(ABC):
    def __init__(self):
        pass

    def __enter__(self):
        return self

    @abstractmethod
    def _get_conn(self) -> Any:
        pass

    @abstractmethod
    def insert_messages(self, messages: list) -> None:
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


class PgDatabase(Database):
    def __init__(self):
        pool = init_connection_engine()

        self.session = Session(pool)
        self.session.begin()

    def _get_conn(self) -> Any:
        pass

    def insert_messages(self, messages: list) -> None:
        pass

    def upsert_channel(self, channel) -> None:
        self.session.add(channel)

        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e

    def upsert_channel_data(self, channel_id, data) -> None:
        pass

    def get_channel_by_id(self, channel_id) -> Optional[Channel]:
        return self.session.query(Channel).filter_by(channel_id=channel_id).first()
