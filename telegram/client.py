import json

from telethon import TelegramClient as AsyncTelegram
from telethon.tl import functions

from .common import logger, config


class AsyncTelegramClient:
    def __init__(self):
        self._client = AsyncTelegram("anon", config["api_id"], config["api_hash"])

    async def fetch_messages(self, channel, size=100, max_id=None, min_id=None):
        pass

    async def get_channel_info(self, channel):
        async with self._client as client:
            try:
                data = await client(
                    functions.channels.GetFullChannelRequest(channel=channel)
                )
            except ValueError as e:
                logger.warning(str(e))
                return None

        return json.loads(data.to_json())

    async def get_channel_users(self, channel, limit=1000):
        async with self._client as client:
            try:
                participants = await client.get_participants(channel, limit)
            except ChatAdminRequiredError as e:
                logger.warning(str(e))
                return None

        return participants

    async def get_channels(self, limit=1000):
        async with self._client as client:
            try:
                dialogs = await client.get_dialogs(limit)
                channels = [
                    dialog
                    for dialog in dialogs
                    if not dialog.is_group and dialog.is_channel
                ]
            except ValueError as e:
                logger.warning(str(e))
                return None

        return channels

    async def get_me(self):
        async with self._client as client:
            try:
                me = await client.get_me()
            except ValueError as e:
                logger.warning(str(e))
                return None

        return me
