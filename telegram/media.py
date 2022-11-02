import os

from .client import TelegramClient
from .common import logger
from .database import Database


async def download_media(client: TelegramClient, db: Database) -> None:
    # Get channels from chat history
    channels = await client.get_channels()
    selected_channels = [channels[0]]

    selected_dialogs = selected_channels

    for dialog in selected_dialogs:
        logger.info(f"Getting messages from dialog {dialog.title}")

        folderpath = os.path.join("downloads", dialog.title)
        if not os.path.exists(folderpath):
            os.makedirs(folderpath)

        messages = await client.fetch_messages(dialog=dialog, limit=100)
        for message in messages:
            if message.media is not None:
                filepath = os.path.join(folderpath, str(message.id))
                await client.get_media(message=message, filename=filepath)
