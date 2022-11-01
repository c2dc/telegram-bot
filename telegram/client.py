import json
from abc import ABC, abstractmethod
from typing import List, Optional

from telethon import TelegramClient as AsyncTelegram
from telethon import errors
from telethon.tl import functions, types

from .common import config, logger


class TelegramClient(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    async def fetch_messages(
        self,
        dialog: Optional[types.Dialog],
        limit: int = 100,
        max_id: Optional[int] = None,
        min_id: Optional[int] = None,
        reverse: bool = True,
    ) -> List[types.Message]:
        pass

    @abstractmethod
    async def get_media(self, message: types.Message, filename: str) -> None:
        pass

    @abstractmethod
    async def get_channel_info(self, channel: types.Channel) -> types.messages.ChatFull:
        pass

    @abstractmethod
    async def get_channel_users(
        self, channel: types.Channel, limit: float = 1000
    ) -> List[types.User]:
        pass

    @abstractmethod
    async def get_channels(self, limit: float = 1000) -> List[types.Dialog]:
        pass

    @abstractmethod
    async def get_groups(self, limit: float = 1000) -> List[types.Dialog]:
        pass

    @abstractmethod
    async def get_me(self) -> types.User:
        pass

    @abstractmethod
    async def join_private_channel(self, hash: str) -> None:
        pass

    @abstractmethod
    async def join_public_channel(self, link: str) -> None:
        pass


class AsyncTelegramClient(TelegramClient):
    def __init__(self) -> None:
        self._client = AsyncTelegram(
            f'config/{config["session"]}', config["api_id"], config["api_hash"]
        )

    async def fetch_messages(
        self, dialog, limit=100, max_id=None, min_id=None, reverse=True
    ):
        async with self._client as client:
            try:
                params = [dialog, limit]
                kwargs = {}

                for key in ["max_id", "min_id", "reverse"]:
                    if locals()[key] is not None:
                        kwargs[key] = locals()[key]

                messages = await client.get_messages(*params, **kwargs)
            except ValueError as e:
                logger.warning(str(e))
                raise e

        return messages

    async def get_media(self, message: types.Message, filename: str) -> None:
        def callback(current, total):
            print(
                f"Downloaded {current} out of {total} total bytes: {(current / total):.2%}"
            )

        async with self._client as client:
            try:
                print(f"Trying to create {filename}")
                result = await client.download_media(
                    message=message, file=filename, progress_callback=callback
                )
                print(result)
            except Exception as e:
                logger.warning(str(e))
                raise e

    async def get_channel_info(self, channel: types.Channel) -> types.messages.ChatFull:
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

    async def join_private_channel(self, hash: str) -> None:
        async with self._client as client:
            try:
                # Check if its valid
                chat_invite = await client(
                    functions.messages.CheckChatInviteRequest(hash=hash)
                )

                # Do not join groups/channels we are already members
                if isinstance(chat_invite, types.ChatInviteAlready):
                    chat = chat_invite.chat
                    logger.info(
                        f"Won't join channel {chat.title}, since we are already members"
                    )
                    return

                # Do not join small groups/channels
                participants = chat_invite.participants_count
                if participants > 50:
                    logger.info(
                        f"Joining channel {chat_invite.title} with {participants} participants"
                    )
                    await client(functions.messages.ImportChatInviteRequest(hash))
                else:
                    logger.info(
                        f"Won't join channel {chat_invite.title} with only {participants} participants"
                    )
            except errors.InviteHashExpiredError as e:
                logger.warning(str(e))
                pass
            except errors.UserAlreadyParticipantError as e:
                logger.warning(str(e))
                pass
            except errors.UsernameNotOccupiedError as e:
                logger.warning(str(e))
                pass
            except Exception as e:
                logger.warning(str(e))
                pass

    async def join_public_channel(self, link: str) -> None:
        async with self._client as client:
            try:
                entity = await client.get_entity(link)
                if isinstance(entity, types.Channel):
                    logger.info(
                        f"Joining channel {entity.title} with {entity.participants_count} participants"
                    )
                    await client(functions.channels.JoinChannelRequest(entity))
            except errors.ChannelPrivateError as e:
                logger.warning(str(e))
                pass
            except errors.UsernameInvalidError as e:
                logger.warning(str(e))
                pass
            except errors.UsernameNotOccupiedError as e:
                logger.warning(str(e))
                pass
            except Exception as e:
                logger.warning(str(e))
                pass

    async def get_chat_invite(
        self, link: str, min_participants: int = 50
    ) -> Optional[types.ChatInvite]:
        async with self._client as client:
            try:
                # Check if its valid
                chat_invite = await client(
                    functions.messages.CheckChatInviteRequest(hash=hash)
                )

                # Do not join groups/channels we are already members
                if isinstance(chat_invite, types.ChatInviteAlready):
                    chat = chat_invite.chat
                    logger.info(
                        f"Won't join channel {chat.title}, since we are already members"
                    )
                    return None

                # Do not join small groups/channels
                participants = chat_invite.participants_count
                if participants < min_participants:
                    logger.info(
                        f"Won't join channel {chat_invite.title} with only {participants} participants"
                    )
                    return None

                return chat_invite

            except errors.InviteHashExpiredError as e:
                return None
            except errors.InviteHashInvalidError as e:
                return None
