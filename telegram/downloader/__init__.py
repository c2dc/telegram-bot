import asyncio
from typing import Any

from ..client import TelegramClient
from ..database import Database
from ..utils import select_dialogs
from .dialog import download_dialog
from .media import download_media

USER_FULL_DELAY = 1.5
CHAT_FULL_DELAY = 1.5
MEDIA_DELAY = 3.0
HISTORY_DELAY = 1.0


class Downloader:
    """
    Download dialogs and their associated data, and dump them.
    Make Telegram API requests and sleep for the appropriate time.
    """

    def __init__(
        self, client: TelegramClient, db: Database, loop: asyncio.AbstractEventLoop
    ) -> None:
        self.db = db
        self.client = client
        self.loop = loop or asyncio.get_event_loop()

        # We're gonna need a few queues if we want to do things concurrently.
        # None values should be inserted to notify that the dump has finished.
        self._media_queue: asyncio.Queue[Any] = asyncio.Queue()
        self._user_queue: asyncio.Queue[Any] = asyncio.Queue()
        self._chat_queue: asyncio.Queue[Any] = asyncio.Queue()

        self._running = False

    async def download_dialogs(self) -> None:
        dialogs = await self.client.get_dialogs()
        selected_dialogs = select_dialogs(dialogs)

        for dialog in selected_dialogs:
            await download_dialog(client=self.client, db=self.db, dialog=dialog)

    async def download_past_media(self, dialog_id: int) -> None:
        dialogs = []
        if dialog_id != 0:
            dialog = await self.client.get_entity_from_id(dialog_id)
            if dialog:
                dialogs.append(dialog)
        else:
            dialogs = await self.client.get_dialogs()

        for dialog in dialogs:
            await download_media(client=self.client, db=self.db, dialog=dialog)
