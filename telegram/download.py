import asyncio
import os
import time
from typing import Any, List

from telethon.tl import types

from .client import TelegramClient
from .common import BATCH_SIZE, logger
from .database import Database
from .models import Channel, Message
from .utils import select_dialogs

USER_FULL_DELAY = 1.5
CHAT_FULL_DELAY = 1.5
MEDIA_DELAY = 3.0
HISTORY_DELAY = 1.0


class Downloader:
    """
    Download dialogs and their associated data, and dump them.
    Make Telegram API requests and sleep for the appropriate time.
    """

    def __init__(self, client: TelegramClient, db: Database) -> None:
        self.db = db
        self.client = client

        self._checked_entity_ids: set[int] = set()

        # We're gonna need a few queues if we want to do things concurrently.
        # None values should be inserted to notify that the dump has finished.
        self._media_queue: asyncio.Queue[Any] = asyncio.Queue()

        self._running = False

    def _check_media(self, message: types.Message) -> bool:
        if not message.media:
            return False

        return True

    def _create_download_folder(self, dialog: types.Dialog) -> str:
        folderpath = os.path.join("downloads", dialog.title)
        if not os.path.exists(folderpath):
            os.makedirs(folderpath)

        return folderpath

    def enqueue_media(self, messages: List[types.Message]) -> None:
        for message in messages:
            self._media_queue.put_nowait(message)

    async def _media_consumer(self, queue) -> None:
        while self._running:
            start = time.time()

            message = await queue.get()
            filename = os.path.join(self._folderpath, str(message.id))

            self._incomplete_download = filename
            await self.client.get_media(message=message, filename=filename)
            self._incomplete_download = None  # type: ignore

            queue.task_done()

            delay = max(MEDIA_DELAY - (time.time() - start), 0)
            await asyncio.sleep(delay)

    async def start(self, dialog: types.Dialog) -> None:
        """
        Starts the dump with the given dialog.
        """

        self._running = True
        self._incomplete_download = None  # type: ignore
        self._folderpath: str = self._create_download_folder(dialog)

        # Create asyncio Tasks
        asyncio.ensure_future(self._media_consumer(self._media_queue))

        # Resume entities and media download
        # self.enqueue_media()
        try:
            max_message_id = self.db.get_max_message_id(dialog.id)

            count = 0
            while self._running:
                start = time.time()

                messages = await self.client.fetch_messages(
                    dialog=dialog, limit=BATCH_SIZE, min_id=max_message_id
                )

                # Stop if there are no new messages
                count += len(messages)
                if messages is None or len(messages) == 0:
                    logger.info(
                        f"Downloaded {count} new messages from dialog {dialog.name}"
                    )
                    break

                # Insert messages into the database
                records = [
                    Message(
                        message=message,
                        channel_id=dialog.id,
                    )
                    for message in messages
                    if isinstance(message, types.Message)
                ]
                self.db.insert_messages(records)

                # Enqueue messages with media to be downloaded
                messages_with_media = [
                    message for message in messages if self._check_media(message)
                ]
                self.enqueue_media(messages_with_media)

                # Update max_message_id
                max_id = max([message.id for message in messages])
                if max_message_id is None or max_message_id < max_id:
                    max_message_id = max_id

                # Upsert dialog with updated max_message_id
                self.db.upsert_channel(
                    Channel(
                        channel_id=dialog.id,
                        name=dialog.name,
                        max_message_id=max_message_id,  # type: ignore
                    )
                )

                # Commit transaction
                self.db.commit_changes()

                delay = max(HISTORY_DELAY - (time.time() - start), 0)
                if delay > HISTORY_DELAY:
                    delay = HISTORY_DELAY
                await asyncio.sleep(delay)

            await self._media_queue.join()

        finally:
            self._running = False

            # # If the download was interrupted and there is media left in the
            # # queue we want to save them into the database for the next run.
            # media = []
            # while not self._media_queue.empty():
            #     media.append(self._media_queue.get_nowait())
            # # self.db.save_resume_media(media)

            # if media:
            #     self.db.commit_changes()

            # Delete partially-downloaded files
            if self._incomplete_download is not None and os.path.isfile(
                self._incomplete_download
            ):
                os.remove(self._incomplete_download)

    async def download_dialogs(self) -> None:
        """
        Perform a dump of the dialogs we've been told to act on.
        """

        dialogs = await self.client.get_dialogs()
        selected_dialogs = select_dialogs(dialogs)

        for dialog in selected_dialogs:
            logger.info(f"Getting messages from dialog {dialog.title}")

            # If the dialog is not in the database, initialize it
            if self.db.get_channel_by_id(dialog.id) is None:
                self.db.upsert_channel(
                    channel=Channel(
                        channel_id=dialog.id,
                        name=dialog.name,
                    )
                )
                self.db.commit_changes()

            # Ingest new messages
            await self.start(dialog)

    async def download_past_media(self, dialog_id: int) -> None:
        """
        Downloads the past media that has already been dumped into the
        database but has not been downloaded for the given target ID yet.

        Media which formatted filename results in an already-existing file
        will be *ignored* and not re-downloaded again.
        """

        dialogs = []
        if dialog_id != 0:
            dialog = await self.client.get_entity_from_id(dialog_id)
            if dialog:
                dialogs.append(dialog)
        else:
            dialogs = await self.client.get_dialogs()

        for dialog in dialogs:
            await download_media(client=self.client, db=self.db, dialog=dialog)
