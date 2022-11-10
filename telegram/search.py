import asyncio
import os
import re
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List

from tqdm import tqdm
from twarc.client2 import Twarc2

from .client import TelegramClient
from .common import CHAT_DELAY, config, logger
from .database import Database


class TelegramLink(Enum):
    PUBLIC = 1
    PRIVATE = 2
    INSTANT_VIEW = 3
    EMBEDDED = 4
    UNKNOWN = 5


class Searcher:
    def __init__(self, args, client: TelegramClient, db: Database):
        self.tl_client = client

        if args.search_twitter:
            self.tw_client = Twarc2(
                consumer_key=config["consumer_key"],
                consumer_secret=config["consumer_secret"],
            )

        if args.search_messages:
            self.db = db

        # Patterns for different telegram invite links
        self.base_pattern = re.compile(
            "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/)([a-zA-Z0-9_\+]+)(\/\S*)?"
        )
        self.public_pattern = re.compile(
            "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/)([a-zA-Z0-9_]+)$"
        )
        self.private_pattern = re.compile(
            "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/)(joinchat\/|\+)([a-zA-Z0-9_]+)$"
        )
        self.instant_view_pattern = re.compile(
            "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/iv\?rhash=)([a-z0-9]+)&url=(.*)$"
        )
        self.embedded_pattern = re.compile(
            "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/)([a-zA-Z0-9_]+)\/([0-9]+)$"
        )

    def _match_link(self, link: str) -> TelegramLink:
        public_match = self.public_pattern.search(link)
        private_match = self.private_pattern.search(link)
        embedded_match = self.embedded_pattern.search(link)
        instant_view_match = self.instant_view_pattern.search(link)

        if public_match:
            return TelegramLink.PUBLIC
        elif private_match:
            return TelegramLink.PRIVATE
        elif embedded_match:
            return TelegramLink.EMBEDDED
        elif instant_view_match:
            return TelegramLink.INSTANT_VIEW
        else:
            logger.error(f"Uncaught link pattern: {link}")
            return TelegramLink.UNKNOWN

    async def _join_invite_links(self, invite_links: List[str]) -> None:
        for link in invite_links:
            match self._match_link(link):
                case TelegramLink.PUBLIC:
                    await self.tl_client.join_public_channel(link)
                case TelegramLink.PRIVATE:
                    hash = "/".join(link.split("/")[:-1])
                    await self.tl_client.join_private_channel(hash=hash)
                case _:
                    logger.error(f"Uncaught link pattern: {link}")
                    pass

    async def _filter_invite_links(self, invite_links: List[str]) -> List[str]:
        urls = set()
        final_urls = set()

        # First, try and reduce list size by extracting only private and public
        # links and removing duplicates
        for link in invite_links:
            match self._match_link(link):
                case TelegramLink.PUBLIC:
                    urls.add(link)
                case TelegramLink.EMBEDDED:
                    link = "/".join(link.split("/")[:-1])
                    urls.add(link)
                case TelegramLink.PRIVATE:
                    urls.add(link)
                case TelegramLink.INSTANT_VIEW:
                    pass
                case _:
                    pass

        # For a smaller list, use Telegram's API to check if we should join
        for link in tqdm(urls):
            start = time.time()

            match self._match_link(link):
                case TelegramLink.PUBLIC:
                    if await self.tl_client.check_public_link(link=link):
                        final_urls.add(link)
                case TelegramLink.PRIVATE:
                    if await self.tl_client.check_private_link(link=link):
                        final_urls.add(link)
                case _:
                    pass

            delay = max(CHAT_DELAY - (time.time() - start), 0)
            await asyncio.sleep(delay)

        return list(final_urls)

    async def _get_twitter_invite_links(self) -> List[str]:
        urls = set()

        # Start and end times must be in UTC
        start_time = datetime.now(timezone.utc) + timedelta(days=-365 * 2)
        end_time = datetime.now(timezone.utc) + timedelta(seconds=-30)

        with open("config/search_queries.txt", "r") as f:
            queries = [query.strip() for query in f.readlines()]

        for query in queries:
            query = f'{query} "t.me" place_country:BR'
            logger.info(f"Searching twitter for: {query}")

            # search_results is a generator, max_results is max tweets per page, 100 max for full archive search with all expansions.
            search_results = self.tw_client.search_all(
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
                            if self.base_pattern.match(url_to_add):
                                urls.add(url_to_add)

        return list(urls)

    async def _get_telegram_invite_links(self) -> List[str]:
        urls = set()
        print(self.db)
        messages = self.db.get_messages_with_pattern(pattern="%t.me%")
        for message in messages:
            # Join group returns from re.findall
            urls_to_add = ["".join(url) for url in self.base_pattern.findall(message)]

            # Remove https?:// substring from string
            urls_to_add = [re.sub("https?:\/\/", "", url) for url in urls_to_add]

            # Add links to set
            urls.update(urls_to_add)

        return list(urls)

    async def search_twitter(self) -> None:
        filename = os.path.join("config", "twitter_invite_links.txt")

        # Search twitter if no query results are available
        if not os.path.exists(filename):
            unfiltered_links = await self._get_twitter_invite_links()
            invite_links = await self._filter_invite_links(unfiltered_links)
            with open(filename, "w") as f:
                for invite_link in invite_links:
                    f.write(f"{invite_link}\n")

        # Load invite_links from already available query results
        else:
            with open(filename, "r") as f:
                invite_links = f.readlines()
                invite_links = [link.strip() for link in invite_links]

        await self._join_invite_links(invite_links)

    async def search_messages(self) -> None:
        filename = os.path.join("config", "telegram_invite_links.txt")

        # Search telegram database if no query results are available
        if not os.path.exists(filename):
            unfiltered_links = await self._get_telegram_invite_links()
            invite_links = await self._filter_invite_links(unfiltered_links)
            with open(filename, "w") as f:
                for invite_link in invite_links:
                    f.write(f"{invite_link}\n")

        # Load invite_links from already available query results
        else:
            with open(filename, "r") as f:
                invite_links = f.readlines()
                invite_links = [link.strip() for link in invite_links]

        await self._join_invite_links(invite_links)
