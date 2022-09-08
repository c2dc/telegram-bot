from .common import logger, config

from typing import Any
from abc import ABC, abstractmethod


class Database(ABC):
    def __init__(self):
        pass

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
        pass

    def _get_conn(self) -> Any:
        pass

    def insert_messages(self, messages: list) -> None:
        pass

    def upsert_channel(self, channel) -> None:
        pass

    def upsert_channel_data(self, channel_id, data) -> None:
        pass

    def get_channel_by_id(self, channel_id) -> Any:
        pass
