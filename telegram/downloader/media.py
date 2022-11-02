import os

from telethon.tl import types

from ..client import TelegramClient
from ..common import logger
from ..database import Database


async def download_media(
    client: TelegramClient, db: Database, dialog: types.Dialog
) -> None:
    logger.info(f"Downloading past media from dialog {dialog.title}")

    folderpath = os.path.join("downloads", dialog.title)
    if not os.path.exists(folderpath):
        os.makedirs(folderpath)

    messages = await client.fetch_messages(dialog=dialog, limit=100)
    for message in messages:
        if message.media is not None:
            filepath = os.path.join(folderpath, str(message.id))
            await client.get_media(message=message, filename=filepath)
