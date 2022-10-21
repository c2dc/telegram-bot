from telethon import types

from telegram.client import TelegramClient
from telegram.common import BATCH_SIZE, logger
from telegram.database import Database
from telegram.models import Channel, Message
from telegram.utils import select_channels, select_groups


async def ingest_dialog(
    client: TelegramClient,
    db: Database,
    dialog: types.Dialog,
    max_message_id: int = None,
):
    logger.info(f"Checking for new messages from dialog {dialog.name}...")

    count = 0
    while True:
        # Get messages from dialog with ID higher than previous max_message_id
        messages = await client.fetch_messages(
            dialog=dialog, limit=BATCH_SIZE, min_id=max_message_id
        )

        # Stop if there are no new messages
        count += len(messages)
        if messages is None or len(messages) == 0:
            logger.info(f"Downloaded {count} new messages from dialog {dialog.name}")
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
        db.insert_messages(records)

        # Update max_message_id
        max_id = max([message.id for message in messages])
        if max_message_id is None or max_message_id < max_id:
            max_message_id = max_id

        # Upsert dialog with updated max_message_id
        db.upsert_channel(
            Channel(
                channel_id=dialog.id,
                name=dialog.name,
                max_message_id=max_message_id,  # type: ignore
            )
        )

        # Commit transaction
        db.commit_changes()


async def download_dialogs(client: TelegramClient, db: Database) -> None:
    # Get channels from chat history
    channels = await client.get_channels()
    selected_channels = select_channels(channels)

    # Get groups from chat history
    groups = await client.get_groups()
    selected_groups = select_groups(groups)

    selected_dialogs = selected_channels + selected_groups

    for dialog in selected_dialogs:
        logger.info(f"Getting messages from dialog {dialog.title}")

        # If the dialog is not in the database, initialize it
        if db.get_channel_by_id(dialog.id) is None:
            logger.info(f"Initializing dialog {dialog.name} in the database")
            db.upsert_channel(
                channel=Channel(
                    channel_id=dialog.id,
                    name=dialog.name,
                )
            )
            db.commit_changes()

        # Ingest new messages
        await ingest_dialog(
            client, db, dialog, max_message_id=db.get_max_message_id(dialog.id)
        )
