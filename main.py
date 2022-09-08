import asyncio

from telegram.models import Message
from telegram.common import logger
from telegram.database import PgDatabase
from telegram.client import AsyncTelegramClient
from telethon.tl import types

db = PgDatabase()
client = AsyncTelegramClient()


async def ingest_channel(channel: types.Channel, stop_point: int = None):
    BATCH_SIZE = 250
    current_message_id = None
    min_message_id = None
    max_message_id = None

    condition = False
    while condition:
        records = []

        messages = await client.fetch_messages(
            channel=channel, limit=BATCH_SIZE, max_id=current_message_id
        )

        if messages:
            min_id = min([message.id for message in messages])
            if min_message_id is None or min_message_id > min_id:
                min_message_id = min_id

            max_id = max([message.id for message in messages])
            if max_message_id is None or max_message_id < max_id:
                max_message_id = max_id

            for message in messages:
                current_message_id = message.id

                records.append(
                    Message(
                        message_id=message.id,
                        channel_id=channel.id,
                        data=message.to_json(),
                    )
                )

        db.insert_messages(records)
        condition = False


async def main():
    channels = await client.get_channels()
    for channel in channels:
        logger.info(f"Getting messages from channel {channel.title}")

        channel_info = db.get_channel_by_id(channel.id)
        print(channel_info)

        # If the channel is not in the DB, get the entire history for the channel
        if channel_info is None:
            db.upsert_channel_data(channel_id=channel.id, data=channel.to_dict())
            await ingest_channel(channel)
        else:
            await ingest_channel(channel, channel_info[5])

    groups = await client.get_groups()
    for group in groups:
        logger.info(f"Getting messages from group {group.title}")


if __name__ == "__main__":
    asyncio.run(main())
