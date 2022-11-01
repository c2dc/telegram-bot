import os
import re
from datetime import datetime, timedelta, timezone
from typing import List

from twarc.client2 import Twarc2

from .client import AsyncTelegramClient
from .common import config, logger
from .database import Database

tl_client = AsyncTelegramClient()


async def join_invite_links(invite_links: List[str]) -> None:
    public_pattern = "(https?:\/\/)?(www[.])?(telegram|t)\.me\/([a-zA-Z0-9_]+)$"
    private_pattern = (
        "(https?:\/\/)?(www[.])?(telegram|t)\.me\/(joinchat\/|\+)([a-zA-Z0-9_]+)$"
    )
    instant_view_pattern = (
        "(https?:\/\/)?(www[.])?(telegram|t)\.me\/iv\?rhash=([a-z0-9]+)&url=(.*)$"
    )
    embedded_pattern = (
        "(https?:\/\/)?(www[.])?(telegram|t)\.me\/([a-zA-Z0-9_]+)\/([0-9]+)$"
    )

    for link in invite_links:
        public_match = re.search(public_pattern, link)
        private_match = re.search(private_pattern, link)
        embedded_match = re.search(embedded_pattern, link)
        instant_view_match = re.search(instant_view_pattern, link)

        if public_match:
            await tl_client.join_public_channel(link)
        elif embedded_match:
            link = "/".join(link.split("/")[:-1])
            await tl_client.join_public_channel(link)
        elif private_match:
            hash = private_match.group(5)
            await tl_client.join_private_channel(hash=hash)
        elif instant_view_match:
            pass
        else:
            logger.error(f"Uncaught link pattern: {link}")
            pass


def get_twitter_invite_links() -> List[str]:
    tw_client = Twarc2(
        consumer_key=config["consumer_key"], consumer_secret=config["consumer_secret"]
    )

    urls = set()

    # Start and end times must be in UTC
    start_time = datetime.now(timezone.utc) + timedelta(days=-365 * 2)
    end_time = datetime.now(timezone.utc) + timedelta(seconds=-30)

    # Pattern for telegram links
    pattern = re.compile(
        "(https?:\/\/)?(www[.])?(telegram|t)\.me\/[a-zA-Z0-9_\+]+(\/\S*)?"
    )

    with open("config/search_queries.txt", "r") as f:
        queries = [query.strip() for query in f.readlines()]

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
                if tweet["entities"] is not None:
                    for url in tweet["entities"]["urls"]:
                        url_to_add = url["expanded_url"]
                        if pattern.match(url_to_add):
                            urls.add(url_to_add)

    return list(urls)


def get_telegram_invite_links(db: Database) -> List[str]:
    urls = set()

    # Pattern for telegram links
    base_pattern = re.compile(
        "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/)([a-zA-Z0-9_\+]+)(\/\S*)?"
    )

    # Patterns for different telegram link types
    public_pattern = re.compile(
        "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/)([a-zA-Z0-9_]+)$"
    )
    private_pattern = re.compile(
        "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/)(joinchat\/|\+)([a-zA-Z0-9_]+)$"
    )
    instant_view_pattern = re.compile(
        "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/)iv\?rhash=([a-z0-9]+)&url=(.*)$"
    )
    embedded_pattern = re.compile(
        "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/)([a-zA-Z0-9_]+)\/([0-9]+)$"
    )

    # Iterates through messages
    messages = db.get_messages_with_pattern(pattern="%t.me%")
    for message in messages:
        urls_to_add = ["".join(url) for url in base_pattern.findall(message)]
        urls_to_add = [re.sub("https?:\/\/", "", url) for url in urls_to_add]

        for url in urls_to_add:
            public_match = public_pattern.search(url)
            private_match = private_pattern.search(url)
            embedded_match = embedded_pattern.search(url)
            instant_view_match = instant_view_pattern.search(url)

            if embedded_pattern.search(url):
                url = "/".join(url.split("/")[:-1])
            urls.add(url)

    return list(urls)


async def search_twitter():
    filename = os.path.join("config", "invite_links.txt")

    # Search twitter if no query results are available
    if not os.path.exists(filename):
        invite_links = get_twitter_invite_links()
        with open(filename, "w") as f:
            for invite_link in invite_links:
                f.write(f"{invite_link}\n")

    # Load invite_links from already available query results
    else:
        with open(filename, "r") as f:
            invite_links = f.readlines()
            invite_links = [link.strip() for link in invite_links]

    await join_invite_links(invite_links)


async def search_telegram(db: Database):
    filename = os.path.join("config", "telegram_invite_links.txt")

    # Search telegram database if no query results are available
    if not os.path.exists(filename):
        invite_links = get_telegram_invite_links(db)
        with open(filename, "w") as f:
            for invite_link in invite_links:
                f.write(f"{invite_link}\n")

    # Load invite_links from already available query results
    else:
        with open(filename, "r") as f:
            invite_links = f.readlines()
            invite_links = [link.strip() for link in invite_links]

    await join_invite_links(invite_links)
