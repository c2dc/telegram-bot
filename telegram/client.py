import json
from typing import List

from telethon import TelegramClient as AsyncTelegram
from telethon.tl import functions
from telethon.tl import types
from telethon import errors

from .common import logger, config


class AsyncTelegramClient:
    def __init__(self):
        self._client = AsyncTelegram(
            config["session"], config["api_id"], config["api_hash"]
        )

    async def fetch_messages(
        self, channel, limit=100, max_id=None, min_id=None, reverse=True
    ):
        async with self._client as client:
            try:
                params = [channel, limit]
                kwargs = {}

                for key in ["max_id", "min_id", "reverse"]:
                    if locals()[key] is not None:
                        kwargs[key] = locals()[key]

                messages = await client.get_messages(*params, **kwargs)
            except ValueError as e:
                logger.warning(str(e))
                raise e

        return messages

    async def get_channel_info(self, channel: types.Channel):
        async with self._client as client:
            try:
                data = await client(
                    functions.channels.GetFullChannelRequest(channel=channel)
                )
            except ValueError as e:
                logger.warning(str(e))
                raise e

        return json.loads(data.to_json())

    async def get_channel_users(
        self, channel: types.Channel, limit: float = 1000
    ) -> List[types.User]:
        async with self._client as client:
            try:
                participants = await client.get_participants(channel, limit)
            except errors.ChatAdminRequiredError as e:
                logger.warning(str(e))
                raise e

        return participants

    async def get_channels(self, limit: float = 1000) -> List[types.Dialog]:
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
                raise e

        return channels

    async def get_groups(self, limit: float = 1000) -> List[types.Dialog]:
        async with self._client as client:
            try:
                dialogs = await client.get_dialogs(limit)
                groups = [
                    dialog
                    for dialog in dialogs
                    if dialog.is_group and dialog.is_channel
                ]
            except ValueError as e:
                logger.warning(str(e))
                raise e

        return groups

    async def get_me(self) -> types.User:
        async with self._client as client:
            try:
                me = await client.get_me()
            except ValueError as e:
                logger.warning(str(e))
                raise e

        return me
