import argparse
import asyncio
from contextlib import suppress

from telegram.client import AsyncTelegramClient
from telegram.database import PgDatabase
from telegram.dialog import download_dialogs
from telegram.media import download_media
from telegram.search import search_telegram, search_twitter


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download Telegram data (chats, messages, and media) into a database"
    )

    parser.add_argument(
        "--list-dialogs", action="store_true", help="list dialogs and exit"
    )

    parser.add_argument(
        "--search-twitter",
        help="search for chats to join on twitter",
    )

    parser.add_argument(
        "--search-messages",
        help="search for chats to join on already collected messages",
    )

    parser.add_argument(
        "--download-past-media",
        action="store_true",
        help="download past media (files that were seen before but not downloaded).",
    )

    return parser.parse_args()


async def main(loop):
    """
    The main telegram-bot program. Goes through all the subscribed dialogs and dumps them.
    """
    args = parse_args()

    db = PgDatabase()
    client = AsyncTelegramClient()

    if args.search_twitter:
        return await search_twitter()

    if args.search_messages:
        return await search_telegram(db)

    try:
        if args.download_past_media:
            await download_media(client, db)
        else:
            await download_dialogs(client, db)
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        ret = asyncio.run(main(loop=loop)) or 0
    except KeyboardInterrupt:
        ret = 1

    for task in asyncio.all_tasks(loop=loop):
        task.cancel()
        # Now we should await task to execute it's cancellation.
        # Cancelled task raises asyncio.CancelledError that we can suppress:
        if task.get_coro() == "main":
            continue
        with suppress(asyncio.CancelledError):
            asyncio.run(task)
    loop.stop()
    loop.close()
    exit(ret)
