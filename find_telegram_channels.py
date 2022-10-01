import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import List

from twarc.client2 import Twarc2

from telegram.client import AsyncTelegramClient
from telegram.common import config, logger

tl_client = AsyncTelegramClient()
tw_client = Twarc2(
    consumer_key=config["consumer_key"], consumer_secret=config["consumer_secret"]
)


async def join_invite_links(invite_links: List[str]) -> None:
    public_pattern = "(https?:\/\/)?(www[.])?(telegram|t)\.me\/([a-zA-Z0-9_]+)$"
    private_pattern = (
        "(https?:\/\/)?(www[.])?(telegram|t)\.me\/(joinchat\/|\+)([a-zA-Z0-9_]+)$"
    )

    for link in invite_links:
        public_match = re.search(public_pattern, link)
        private_match = re.search(private_pattern, link)
        if public_match:
            await tl_client.join_public_channel(link)
        elif private_match:
            hash = private_match.group(5)
            await tl_client.join_private_channel(hash=hash)
        else:
            raise Exception(f"Uncaught link pattern: {link}")


def get_invite_links() -> List[str]:
    urls = set()

    # Start and end times must be in UTC
    start_time = datetime.now(timezone.utc) + timedelta(days=-365 * 2)
    end_time = datetime.now(timezone.utc) + timedelta(seconds=-30)

    # Pattern for telegram links
    pattern = re.compile(
        "(https?:\/\/)?(www[.])?(telegram|t)\.me\/[a-zA-Z0-9_\+]+(\/\S*)?"
    )

    queries = [
        "grupo direita telegram",
        "grupo direita norte",
        "grupo direita nordeste",
        "grupo direita sudeste",
        "grupo direita sul",
        "grupo direita centro oeste",
        "grupo direita bolsonaro",
        "grupo bolsonaro telegram",
        "grupo bolsonaro norte",
        "grupo bolsonaro nordeste",
        "grupo bolsonaro sudeste",
        "grupo bolsonaro sul",
        "grupo bolsonaro centro oeste",
        "grupo esquerda telegram",
        "grupo esquerda norte",
        "grupo esquerda nordeste",
        "grupo esquerda sudeste",
        "grupo esquerda sul",
        "grupo esquerda centro oeste",
        "grupo lula telegram",
        "grupo lula norte",
        "grupo lula nordeste",
        "grupo lula sudeste",
        "grupo lula sul",
        "grupo lula centro oeste",
        "grupo ciro telegram",
        "grupo ciro norte",
        "grupo ciro nordeste",
        "grupo ciro sudeste",
        "grupo ciro sul",
        "grupo ciro centro oeste",
    ]

    for query in queries:
        query = f'{query} "t.me" place_country:BR'
        logger.info(f"Searching twitter for: {query}")

        # search_results is a generator, max_results is max tweets per page, 100 max for full archive search with all expansions.
        search_results = tw_client.search_all(
            query=query,
            start_time=start_time,
            end_time=end_time,
            max_results=100,
        )

        # Get all urls from results:
        for page in search_results:
            for tweet in page["data"]:
                for url in tweet["entities"]["urls"]:
                    url_to_add = url["expanded_url"]
                    if pattern.match(url_to_add):
                        urls.add(url_to_add)

    return list(urls)


async def main():
    invite_links = get_invite_links()
    await join_invite_links(invite_links)


if __name__ == "__main__":
    asyncio.run(main())
