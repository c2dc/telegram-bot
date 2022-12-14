import json
from abc import ABC, abstractmethod
from typing import Callable, List, Optional

from telethon import TelegramClient as AsyncTelegram
from telethon import errors
from telethon.tl import functions, types

from .common import config, logger


def _handle_chat(chat: types.Chat, min_participants: int = 50) -> Optional[types.Chat]:
    # Do not consider unuseful options
    if (
        isinstance(chat, types.ChannelForbidden)
        or isinstance(chat, types.ChatForbidden)
        or isinstance(chat, types.ChatEmpty)
    ):
        return None

    elif isinstance(chat, types.Channel):
        # Do not join small channels
        if (
            chat.participants_count is not None
            and chat.participants_count < min_participants
        ):
            return None

        # Do not join if there's need for human approval
        if hasattr(chat, "join_request") and chat.join_request:
            return None

    elif isinstance(chat, types.Chat):
        # Do not join small chats
        if (
            chat.participants_count is not None
            and chat.participants_count < min_participants
        ):
            return None

    return chat


def _handle_chat_invite(
    chat_invite: types.ChatInvite, min_participants: int = 50
) -> Optional[types.ChatInvite]:
    # Do not join small groups/channels
    if (
        chat_invite.participants_count is not None
        and chat_invite.participants_count < min_participants
    ):
        return None

    # Do not join if there's need for admin aproval
    if hasattr(chat_invite, "request_needed") and chat_invite.request_needed:
        return None

    return chat_invite


class TelegramClient(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
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
    async def get_media(
        self, message: types.Message, filename: str, callback: Optional[Callable] = None
    ) -> None:
        pass

    @abstractmethod
    async def get_entity_from_id(self, id: int) -> Optional[types.Dialog]:
        pass

    @abstractmethod
    async def get_dialog_info(self, dialog: types.Dialog) -> types.messages.ChatFull:
        pass

    @abstractmethod
    async def get_dialog_users(
        self, dialog: types.Dialog, limit: int = 1000
    ) -> List[types.User]:
        pass

    @abstractmethod
    async def get_dialogs(self, limit: float = 1000) -> List[types.Dialog]:
        pass

    @abstractmethod
    async def join_private_channel(self, link: str) -> None:
        pass

    @abstractmethod
    async def join_public_channel(self, link: str) -> None:
        pass

    @abstractmethod
    async def check_private_link(self, link: str, min_participants: int = 50) -> bool:
        pass

    @abstractmethod
    async def check_public_link(self, link: str, min_participants: int = 50) -> bool:
        pass


class AsyncTelegramClient(TelegramClient):
    def __init__(self) -> None:
        self.client = AsyncTelegram(
            f'config/{config["session"]}',
            config["api_id"],
            config["api_hash"],
        )

    async def connect(self) -> None:
        await self.client.connect()

    async def disconnect(self) -> None:
        await self.client.disconnect()

    async def fetch_messages(
        self, dialog, limit=100, max_id=None, min_id=None, reverse=True
    ):

        try:
            params = [dialog, limit]
            kwargs = {}

            for key in ["max_id", "min_id", "reverse"]:
                if locals()[key] is not None:
                    kwargs[key] = locals()[key]

            messages = await self.client.get_messages(*params, **kwargs)
        except ValueError as e:
            logger.warning(str(e))
            raise e

        return messages

    async def get_media(
        self, message: types.Message, filename: str, callback: Optional[Callable] = None
    ) -> None:
        try:
            result = await self.client.download_media(
                message=message, file=filename, progress_callback=callback
            )
        except Exception as e:
            logger.warning(str(e))
            raise e

    async def get_entity_from_id(self, id: int) -> Optional[types.Dialog]:
        try:
            entity = await self.client.get_entity(id)
        except ValueError as e:
            logger.warning(str(e))
            return None

        return entity

    async def get_dialog_info(self, dialog: types.Dialog) -> types.messages.ChatFull:
        try:
            data = await self.client(
                functions.channels.GetFullChannelRequest(channel=dialog)
            )
        except ValueError as e:
            logger.warning(str(e))
            raise e

        return json.loads(data.to_json())

    async def get_dialog_users(
        self, dialog: types.Dialog, limit: int = 10000
    ) -> List[types.User]:
        try:
            # Telegram API's limit the number of users we can retrieve to 10k
            participants = await self.client.get_participants(dialog, limit)
        except errors.ChatAdminRequiredError as e:
            logger.warning(str(e))
            return []

        return participants

    async def get_dialogs(self, limit: float = 1000) -> List[types.Dialog]:
        try:
            dialogs = await self.client.get_dialogs(limit)
            dialogs = [
                dialog for dialog in dialogs if dialog.is_group or dialog.is_channel
            ]
        except ValueError as e:
            logger.warning(str(e))
            raise e

        return dialogs

    async def join_private_channel(self, link: str) -> None:
        try:
            # Extract hash from invite link
            hash = "".join(link.split("/")[:-1])
            hash = hash.replace("+", "")

            await self.client(functions.messages.ImportChatInviteRequest(hash=hash))

        except (
            errors.InviteHashExpiredError,
            errors.UserAlreadyParticipantError,
            errors.UsernameNotOccupiedError,
        ) as e:
            pass
        except Exception as e:
            logger.warning(str(e))
            pass

    async def join_public_channel(self, link: str) -> None:
        try:
            entity = await self.client.get_entity(link)

            if isinstance(entity, types.Channel):
                logger.info(f"Joining channel {entity.title}")
                await self.client(functions.channels.JoinChannelRequest(entity))
            elif isinstance(entity, types.Chat):
                logger.info(f"Joining chat {entity.title}")
                await self.client(functions.channels.JoinChannelRequest(entity))

        except (
            errors.ChannelPrivateError,
            errors.UsernameInvalidError,
            errors.UsernameNotOccupiedError,
        ) as e:
            pass
        except Exception as e:
            logger.warning(str(e))
            pass

    async def check_private_link(self, link: str, min_participants: int = 50) -> bool:
        try:
            # Extract hash
            hash = "".join(link.split("/")[:-1])
            hash = hash.replace("+", "")

            # Check if its valid
            chat_invite = await self.client(
                functions.messages.CheckChatInviteRequest(hash=hash)
            )

            match chat_invite:
                case types.ChatInviteAlready():
                    # Do not join groups/channels we are already members
                    return False
                case types.ChatInvite():
                    if _handle_chat_invite(chat_invite, min_participants) is None:
                        return False
                case types.ChatInvitePeek():
                    if _handle_chat(chat_invite.chat, min_participants) is None:
                        return False

            return True

        except (
            errors.ChannelInvalidError,
            errors.ChannelPrivateError,
            errors.UsernameInvalidError,
            errors.UsernameNotOccupiedError,
            errors.InviteHashInvalidError,
            errors.InviteHashExpiredError,
        ) as e:
            return False
        except ValueError as e:
            return False
        except Exception as e:
            logger.warning(str(e))
            return False

    async def check_public_link(self, link: str, min_participants: int = 50) -> bool:
        try:
            entity = await self.client.get_entity(link)

            # Do not consider users
            if isinstance(entity, types.User):
                return False

            if _handle_chat(entity, min_participants) is None:
                return False

            return True

        except (
            errors.ChannelInvalidError,
            errors.ChannelPrivateError,
            errors.UsernameInvalidError,
            errors.UsernameNotOccupiedError,
        ) as e:
            return False
        except ValueError as e:
            return False
        except Exception as e:
            logger.error(str(e))
            return False
