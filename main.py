import asyncio

from telegram.common import logger
from telegram.database import Database
from telegram.client import AsyncTelegramClient

db = Database()
client = AsyncTelegramClient()


def ingest_channel(channel_name: str, channel_id: int, stop_point: int = None):
    pass


async def main():
    channels = await client.get_channels()
    logger.info(f"There's a total of {len(channels)} channels to verify")

    for channel in channels:
        logger.info(f"Checking for new messages from channel {channel.title}...")
        channel_data = await client.get_channel_info(channel)

        channel_id = channel.id
        channel_name = channel.name
        channel_info = db.get_channel_by_id(channel_id)

        # If the channel is not in the DB, let's get the entire history for the channel
        if channel_info is None:
            db.upsert_channel_data(channel_id, channel_data)
            ingest_channel(channel, channel_id)
        else:
            ingest_channel(channel, channel_id, channel_info[5])


if __name__ == "__main__":
    asyncio.run(main())
