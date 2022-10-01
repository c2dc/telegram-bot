import asyncio

from telethon.tl import types

from telegram.client import AsyncTelegramClient
from telegram.common import logger
from telegram.database import PgDatabase
from telegram.models import Channel, Message
from telegram.search import search_telegram, search_twitter
from telegram.utils import Selections, select, select_channels, select_groups

BATCH_SIZE = 500

db = PgDatabase()
client = AsyncTelegramClient()


async def ingest_channel(channel: types.Channel, max_message_id: int = None):
    logger.info(f"Checking for new messages from channel {channel.name}...")

    count = 0
    try:
        while True:
            # Get messages from channel with ID higher than previous max_message_id
            messages = await client.fetch_messages(
                channel=channel, limit=BATCH_SIZE, min_id=max_message_id
            )

            # Stop if there are no new messages
            count += len(messages)
            if messages is None or len(messages) == 0:
                logger.info(
                    f"Downloaded {count} new messages from channel {channel.name}"
                )
                break

            # Insert messages into the database
            records = [
                Message(
                    message_id=message.id,
                    channel_id=channel.id,
                    data=message.to_json(),
                )
                for message in messages
            ]
            db.insert_messages(records)

            # Update max_message_id
            max_id = max([message.id for message in messages])
            if max_message_id is None or max_message_id < max_id:
                max_message_id = max_id

            # Upsert channel with updated max_message_id
            db.upsert_channel(
                Channel(
                    channel_id=channel.id,
                    name=channel.name,
                    max_message_id=max_message_id,
                )
            )

            # Commit transaction
            db.commit_changes()

    except Exception as e:
        logger.error(e)
        raise e


async def download_channels() -> None:
    # Get channels from chat history
    channels = await client.get_channels()
    selected_channels = select_channels(channels)

    for channel in selected_channels:
        logger.info(f"Getting messages from channel {channel.title}")

        # If the channel is not in the database, initialize it
        if db.get_channel_by_id(channel.id) is None:
            logger.info(f"Initializing channel {channel.name} in the database")
            db.upsert_channel(
                channel=Channel(
                    channel_id=channel.id,
                    name=channel.name,
                )
            )
            db.commit_changes()

        # Ingest new messages
        await ingest_channel(channel, max_message_id=db.get_max_message_id(channel.id))


async def download_groups() -> None:
    # Get groups from chat history
    groups = await client.get_groups()
    selected_groups = select_groups(groups)

    for group in selected_groups:
        logger.info(f"Getting messages from group {group.title}")


async def main():
    match select():
        case Selections.SEARCH_TWITTER:
            await search_twitter()
        case Selections.SEARCH_TELEGRAM:
            await search_telegram()
        case Selections.DOWNLOAD_CHANNELS:
            await download_channels()
        case Selections.DOWNLOAD_GROUPS:
            await download_groups()


if __name__ == "__main__":
    asyncio.run(main())
