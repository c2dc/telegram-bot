import asyncio

from telegram.client import AsyncTelegramClient
from telegram.database import PgDatabase
from telegram.dialog import download_dialogs
from telegram.search import search_telegram, search_twitter
from telegram.utils import Selections, select

db = PgDatabase()
client = AsyncTelegramClient()


async def main():
    match select():
        case Selections.SEARCH_TWITTER:
            await search_twitter()
        case Selections.SEARCH_TELEGRAM:
            await search_telegram()
        case Selections.DOWNLOAD_MESSAGES:
            await download_dialogs(client, db)


if __name__ == "__main__":
    asyncio.run(main())
