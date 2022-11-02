import argparse
import asyncio
from contextlib import suppress

from telegram.client import AsyncTelegramClient
from telegram.database import PgDatabase
from telegram.dump import Dumper
from telegram.search import Searcher


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
        nargs="?",
        const=0,
        type=int,
        help="download past media from all chats or from given chat_id",
    )

    return parser.parse_args()


async def main(loop):
    """
    The main telegram-bot program. Goes through all the subscribed dialogs and dumps them.
    """
    args = parse_args()
    db = PgDatabase()
    client = AsyncTelegramClient()

    if args.list_dialogs is True:
        print("--list-dialogs not implemented!")
        pass

    try:
        if args.search_twitter or args.search_messages:
            searcher = Searcher(db)
            if args.search_twitter:
                await searcher.search_twitter()
            elif args.search_messages:
                await searcher.search_telegram()
        else:
            dumper = Dumper(client, db)
            if args.download_past_media is not None:
                await dumper.download_past_media(dialog_id=args.download_past_media)
            else:
                await dumper.download_dialogs()

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
        if task.get_coro() == "main":
            continue
        with suppress(asyncio.CancelledError):
            asyncio.run(task)

    loop.stop()
    loop.close()
    exit(ret)
