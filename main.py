import argparse
import asyncio
from contextlib import suppress

from telegram.client import AsyncTelegramClient
from telegram.common import logger
from telegram.database import PgDatabase
from telegram.download import Downloader
from telegram.search import Searcher
from telegram.utils import print_dialogs


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download Telegram data (chats, messages, and media) into a database"
    )

    parser.add_argument(
        "--list-dialogs", action="store_true", help="list dialogs and exit"
    )

    parser.add_argument(
        "--search-twitter",
        action="store_true",
        help="search for chats to join on twitter",
    )

    parser.add_argument(
        "--search-messages",
        action="store_true",
        help="search for chats to join on already collected messages",
    )

    parser.add_argument(
        "--download-past-media",
        action="store_true",
        help="download past media from all dialogs",
    )

    return parser.parse_args()


async def main():
    """
    The main telegram-bot program. Goes through all the subscribed dialogs and dumps them.
    """
    args = parse_args()
    db = PgDatabase()
    client = AsyncTelegramClient()
    await client.connect()

    if args.list_dialogs is True:
        dialogs = await client.get_dialogs()
        print_dialogs(dialogs)
        return

    try:
        if args.search_twitter or args.search_messages:
            searcher = Searcher(args, client, db)
            if args.search_twitter:
                await searcher.search_twitter()
            elif args.search_messages:
                await searcher.search_messages()
        else:
            downloader = Downloader(client, db)
            if args.download_past_media is True:
                await downloader.download_past_media_from_dialogs()
            else:
                await downloader.download_dialogs()

    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Disconnecting client")
        await client.disconnect()

    logger.info("Exited succesfully")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        ret = loop.run_until_complete(main()) or 0
    except KeyboardInterrupt:
        ret = 1

    for task in asyncio.all_tasks(loop=loop):
        if task.get_coro() == "main":
            continue
        task.cancel()
        with suppress(asyncio.CancelledError):
            loop.run_until_complete(task)

    loop.stop()
    loop.close()
    exit(ret)
