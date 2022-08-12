from .common import logger, config


class Database:
    def __init__(self):
        pass

    def _get_conn(self):
        pass

    def insert_messages(self, messages: list):
        pass

    def upsert_channel(self, channel):
        pass

    def upsert_channel_data(self, channel_id, data):
        pass

    def get_channel_by_id(self, channel_id):
        pass
