import asyncio
import json
import os
import time
from typing import Any, List

from telethon.tl import types
from tqdm import tqdm

from .client import TelegramClient
from .common import BATCH_SIZE, config, logger
from .database import Database
from .models import Channel, Media, Message, ResumeMedia, User, UserChannel

BAR_FORMAT = (
    "{l_bar}{bar}| {n_fmt}/{total_fmt} "
    "[{elapsed}<{remaining}, {rate_noinv_fmt}{postfix}]"
)
DOWNLOAD_PART_SIZE = 256 * 1024

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
        self.whitelist = config.get("whitelist")
        self.blacklist = config.get("blacklist")

        # We're gonna need a few queues if we want to do things concurrently.
        # None values should be inserted to notify that the dump has finished.
        self._media_queue: asyncio.Queue[Any] = asyncio.Queue()

        self._running = False

    def _check_media(self, message: types.Message) -> bool:
        if isinstance(message.media, types.MessageMediaDocument) and isinstance(
            message.media.document, types.Document
        ):
            return True

        if isinstance(message.media, types.MessageMediaPhoto) and isinstance(
            message.media.photo, types.Photo
        ):
            return True

        return False

    def _create_download_folder(self, dialog: types.Dialog) -> str:
        folderpath = os.path.join("downloads", dialog.title)
        if not os.path.exists(folderpath):
            os.makedirs(folderpath)

        return folderpath

    async def _download_media(self, message) -> None:
        filename = os.path.join(self._folderpath, str(message.id))
        if os.path.isfile(filename):
            return

        self._incomplete_download = filename
        await self.client.get_media(message=message, filename=filename)
        self._incomplete_download = None  # type: ignore

    async def _media_consumer(self, queue, bar) -> None:
        while self._running:
            start = time.time()

            message = await queue.get()
            await self._download_media(message)
            queue.task_done()
            bar.update(1)

            delay = max(MEDIA_DELAY - (time.time() - start), 0)
            await asyncio.sleep(delay)

    def enqueue_media(self, messages: List[types.Message]) -> None:
        for message in messages:
            self._media_queue.put_nowait(message)

    async def start(self, dialog: types.Dialog) -> None:
        """
        Starts the dump with the given dialog.
        """

        self._running = True
        self._incomplete_download = None  # type: ignore
        self._folderpath: str = self._create_download_folder(dialog)

        # Create tqdm bars
        med_bar = tqdm(
            unit=" files",
            desc="files",
            total=0,
            bar_format=BAR_FORMAT,
            postfix={"chat": dialog.title},
        )

        # Create asyncio Tasks
        asyncio.ensure_future(self._media_consumer(self._media_queue, med_bar))

        # Resume media download
        resume_media = self.db.get_resume_media(channel_id=dialog.id)
        resume_messages = [
            json.loads(message, object_hook=types.Message) for message in resume_media
        ]
        self.enqueue_media(resume_messages)
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
                message_records = [
                    Message(
                        message=message,
                        channel_id=dialog.id,
                    )
                    for message in messages
                    if isinstance(message, types.Message)
                ]
                self.db.insert_messages(message_records)
                self.db.flush_changes()

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

                # Insert media metadata into the database
                media_records = [
                    Media(message, channel_id=dialog.id)
                    for message in messages
                    if self._check_media(message)
                ]
                self.db.insert_media(media_records)

                # Enqueue messages with media to be downloaded
                messages_with_media = [
                    message for message in messages if self._check_media(message)
                ]
                med_bar.total += len(messages_with_media)
                self.enqueue_media(messages_with_media)

                # Commit transaction
                self.db.commit_changes()

                delay = max(HISTORY_DELAY - (time.time() - start), 0)
                if delay > HISTORY_DELAY:
                    delay = HISTORY_DELAY
                await asyncio.sleep(delay)

            await self._media_queue.join()

        finally:
            self._running = False
            med_bar.n = med_bar.total
            med_bar.close()

            # If the download was interrupted and there is media left in the
            # queue we want to save them into the database for the next run.
            media = []
            while not self._media_queue.empty():
                message = self._media_queue.get_nowait()
                media.append(ResumeMedia(message, channel_id=dialog.id))

            self.db.insert_resume_media(resume_media=media)

            if media:
                self.db.commit_changes()

            # Delete partially-downloaded files
            if self._incomplete_download is not None and os.path.isfile(
                self._incomplete_download
            ):
                os.remove(self._incomplete_download)

    async def download_past_media(self, dialog: types.Dialog) -> None:
        """
        Downloads the past media that has already been dumped into the
        database but has not been downloaded for the given dialog yet.

        Media with formatted filename results in an already-existing file
        will be *ignored* and not re-downloaded again.
        """

        print("Not implemented!")
        pass

    async def download_participants(self, dialog: types.Dialog) -> None:
        users = await self.client.get_dialog_users(dialog=dialog)
        logger.info(f"Downloaded {len(users)} users from dialog {dialog.name}")

        # Insert users into the database
        user_records = [User(user) for user in users]
        self.db.insert_users(user_records)
        self.db.flush_changes()

        # Insert user and channels relationship into the database
        user_channel_records = [
            UserChannel(channel_id=dialog.id, user_id=user.id) for user in users
        ]
        self.db.insert_users_channels(user_channel_records)

        # Commit transaction
        self.db.commit_changes()

    async def download_dialogs(self) -> None:
        """
        Perform a dump of the dialogs we've been told to act on.
        """

        dialogs = await self.client.get_dialogs()
        if self.whitelist:
            dialogs = [dialog for dialog in dialogs if dialog.id in self.whitelist]
        elif self.blacklist:
            dialogs = [dialog for dialog in dialogs if dialog.id not in self.blacklist]

        for dialog in dialogs:
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

    async def download_past_media_from_dialogs(self) -> None:
        """
        Download past media (media we saw but didn't download before) of the
        dialogs we've been told to act on
        """

        dialogs = await self.client.get_dialogs()
        if self.whitelist:
            dialogs = [dialog for dialog in dialogs if dialog.id in self.whitelist]
        elif self.blacklist:
            dialogs = [dialog for dialog in dialogs if dialog.id not in self.blacklist]

        for dialog in dialogs:
            logger.info(f"Getting past media from dialog {dialog.title}")
            await self.download_past_media(dialog=dialog)

    async def download_participants_from_dialogs(self) -> None:
        dialogs = await self.client.get_dialogs()
        if self.whitelist:
            dialogs = [dialog for dialog in dialogs if dialog.id in self.whitelist]
        elif self.blacklist:
            dialogs = [dialog for dialog in dialogs if dialog.id not in self.blacklist]

        for dialog in dialogs:
            logger.info(f"Getting participants from dialog {dialog.title}")

            # If the dialog is not in the database, initialize it
            if self.db.get_channel_by_id(dialog.id) is None:
                self.db.upsert_channel(
                    channel=Channel(
                        channel_id=dialog.id,
                        name=dialog.name,
                    )
                )
                self.db.commit_changes()

            await self.download_participants(dialog=dialog)
