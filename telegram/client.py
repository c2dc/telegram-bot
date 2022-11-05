import json
from abc import ABC, abstractmethod
from typing import List, Optional

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
    async def get_entity_from_id(self, id: int) -> Optional[types.Dialog]:
        pass

    @abstractmethod
    async def get_dialog_info(self, dialog: types.Dialog) -> types.messages.ChatFull:
        pass

    @abstractmethod
    async def get_dialog_users(
        self, dialog: types.Dialog, limit: float = 1000
    ) -> List[types.User]:
        pass

    @abstractmethod
    async def get_dialogs(self, limit: float = 1000) -> List[types.Dialog]:
        pass

    @abstractmethod
    async def join_private_channel(self, hash: str) -> None:
        pass

    @abstractmethod
    async def join_public_channel(self, link: str) -> None:
        pass

    @abstractmethod
    async def get_chat_invite(
        self, hash: str, min_participants: int = 50
    ) -> Optional[types.ChatInvite]:
        pass

    @abstractmethod
    async def get_entity(
        self, link: str, min_participants: int = 50
    ) -> Optional[types.Chat]:
        pass


class AsyncTelegramClient(TelegramClient):
    def __init__(self) -> None:
        self.client = AsyncTelegram(
            f'config/{config["session"]}',
            config["api_id"],
            config["api_hash"],
        )

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

    async def get_media(self, message: types.Message, filename: str) -> None:
        def callback(current, total):
            print(
                f"Downloaded {current} out of {total} total bytes: {(current / total):.2%}"
            )

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
        self, dialog: types.Dialog, limit: float = 1000
    ) -> List[types.User]:
        try:
            participants = await self.client.get_participants(dialog, limit)
        except errors.ChatAdminRequiredError as e:
            logger.warning(str(e))
            raise e

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

    async def join_private_channel(self, hash: str) -> None:
        try:
            # Check if its valid
            chat_invite = await self.client(
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
                await self.client(functions.messages.ImportChatInviteRequest(hash))
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
        try:
            entity = await self.client.get_entity(link)
            if isinstance(entity, types.Channel):
                logger.info(
                    f"Joining channel {entity.title} with {entity.participants_count} participants"
                )
                await self.client(functions.channels.JoinChannelRequest(entity))
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
        self, hash: str, min_participants: int = 50
    ) -> Optional[types.ChatInvite]:
        try:
            # Check if its valid
            chat_invite = await self.client(
                functions.messages.CheckChatInviteRequest(hash=hash)
            )

            # Do not join groups/channels we are already members
            if isinstance(chat_invite, types.ChatInviteAlready):
                chat = chat_invite.chat
                logger.info(
                    f"Won't join channel {chat.title}, since we are already members"
                )
                return None

            if isinstance(chat_invite, types.ChatInvite):
                # Do not join small groups/channels
                if (
                    chat_invite.participants_count is not None
                    and chat_invite.participants_count < min_participants
                ):
                    return None

                # Do not join if there's need for admin aproval
                if (
                    hasattr(chat_invite, "request_needed")
                    and chat_invite.request_needed
                ):
                    return None

            if isinstance(chat_invite, types.ChatInvitePeek):
                chat = chat_invite.chat
                if _handle_chat(chat, min_participants) is None:
                    return None

            return chat_invite

        except (
            errors.ChannelPrivateError,
            errors.UsernameInvalidError,
            errors.UsernameNotOccupiedError,
            errors.InviteHashInvalidError,
            errors.InviteHashExpiredError,
        ) as e:
            return None
        except ValueError as e:
            return None
        except Exception as e:
            logger.warning(str(e))
            return None

    async def get_entity(
        self, link: str, min_participants: int = 50
    ) -> Optional[types.Chat]:
        try:
            entity = await self.client.get_entity(link)

            # Do not consider users
            if isinstance(entity, types.User):
                return None

            return _handle_chat(entity, min_participants)

        except errors.ChannelPrivateError as e:
            return None
        except errors.UsernameInvalidError as e:
            return None
        except errors.UsernameNotOccupiedError as e:
            return None
        except ValueError as e:
            return None
        except Exception as e:
            logger.error(str(e))
            return None
