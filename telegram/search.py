import asyncio
import os
import re
from datetime import datetime, timedelta, timezone
from typing import List

from tqdm import tqdm
from twarc.client2 import Twarc2

from .client import AsyncTelegramClient
from .common import config, logger
from .database import Database


class Searcher:
    def __init__(self, args, db: Database):
        self.tl_client = AsyncTelegramClient()

        if args.search_twitter:
            self.tw_client = Twarc2(
                consumer_key=config["consumer_key"],
                consumer_secret=config["consumer_secret"],
            )

        if args.search_messages:
            self.db = db

    async def _join_invite_links(self, invite_links: List[str]) -> None:
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
                await self.tl_client.join_public_channel(link)
            elif embedded_match:
                link = "/".join(link.split("/")[:-1])
                await self.tl_client.join_public_channel(link)
            elif private_match:
                hash = private_match.group(5)
                await self.tl_client.join_private_channel(hash=hash)
            elif instant_view_match:
                pass
            else:
                logger.error(f"Uncaught link pattern: {link}")
                pass

    def _get_twitter_invite_links(self) -> List[str]:

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
                            if pattern.match(url_to_add):
                                urls.add(url_to_add)

        return list(urls)

    async def _get_telegram_invite_links(self) -> List[str]:
        urls = set()

        # Patterns for different telegram invite links
        base_pattern = re.compile(
            "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/)([a-zA-Z0-9_\+]+)(\/\S*)?"
        )
        public_pattern = re.compile(
            "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/)([a-zA-Z0-9_]+)$"
        )
        private_pattern = re.compile(
            "(https?:\/\/)?(www[.])?(telegram|t)(\.me\/)(joinchat\/|\+)([a-zA-Z0-9_]+)$"
        )

        messages = self.db.get_messages_with_pattern(pattern="%t.me%")
        for message in messages:
            # Join group returns from re.findall
            urls_to_add = ["".join(url) for url in base_pattern.findall(message)]

            # Remove https?:// substring from string
            urls_to_add = [re.sub("https?:\/\/", "", url) for url in urls_to_add]

            for url in urls_to_add:
                private_match = private_pattern.search(url)
                public_match = public_pattern.search(url)

                if private_match or public_match:
                    urls.add(url)

        final_urls = set()
        for url in tqdm(urls):
            private_match = private_pattern.search(url)
            public_match = public_pattern.search(url)

            if private_match:
                hash = "/".join(url.split("/")[:-1])
                chat_invite = await self.tl_client.get_chat_invite(hash)
                final_urls.add(url)
            elif public_match:
                entity = await self.tl_client.get_entity(url)
                final_urls.add(url)

        return list(final_urls)

    async def search_twitter(self):
        filename = os.path.join("config", "twitter_invite_links.txt")

        # Search twitter if no query results are available
        if not os.path.exists(filename):
            invite_links = self._get_twitter_invite_links()
            with open(filename, "w") as f:
                for invite_link in invite_links:
                    f.write(f"{invite_link}\n")

        # Load invite_links from already available query results
        else:
            with open(filename, "r") as f:
                invite_links = f.readlines()
                invite_links = [link.strip() for link in invite_links]

        await self._join_invite_links(invite_links)

    async def search_messages(self):
        filename = os.path.join("config", "telegram_invite_links.txt")

        # Search telegram database if no query results are available
        if not os.path.exists(filename):
            invite_links = await self._get_telegram_invite_links()
            with open(filename, "w") as f:
                for invite_link in invite_links:
                    f.write(f"{invite_link}\n")

        # Load invite_links from already available query results
        else:
            with open(filename, "r") as f:
                invite_links = f.readlines()
                invite_links = [link.strip() for link in invite_links]

        await self._join_invite_links(invite_links)
