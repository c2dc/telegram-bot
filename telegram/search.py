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
    EMBEDDED = 3
    MESSAGE_LINK = 4
    IGNORE = 5
    UNKNOWN = 6


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
        #
        # You can read more at https://corefork.telegram.org/api/links
        base = "(https?:\/\/)?(www[.])?(telegram|t)(\.me|\.dog)"
        self.base_pattern = re.compile(base + "(\/[a-zA-Z0-9_\-\?\+\=]+)+")
        self.phone_pattern = re.compile(base + "(\/)(\+[0-9]+)$")
        self.private_pattern = re.compile(
            base + "(\/)(joinchat\/|\+)([a-zA-Z0-9_\-]+)$"
        )
        self.embedded_pattern = re.compile(base + "(\/[a-zA-Z0-9_\-]+)((\/|\?)\S*)$")
        self.message_link_pattern = re.compile(base + "(\/)(c|s)(\/[a-zA-Z0-9_\-]+)+$")
        self.message_link_ignore_pattern = re.compile(
            base + "(\/[0-9]+\?)(single|comment=)(\/?[a-zA-Z0-9_\-]+)*$"
        )
        self.instant_view_pattern = re.compile(
            base + "(\/iv\?)(rhash=[a-z0-9\%]+&)?url=(.*)$"
        )
        self.ignore_pattern = re.compile(
            base
            + "(\/)(share|addstickers|addemoji|addtheme|proxy|socks)((\/|\?)[a-zA-Z0-9_\-\?]+)+"
        )
        self.public_pattern = re.compile(base + "(\/[a-zA-Z0-9_\-=]+)$")

    def _match_link(self, link: str) -> TelegramLink:
        phone_match = self.phone_pattern.search(link)
        private_match = self.private_pattern.search(link)
        instant_view_match = self.instant_view_pattern.search(link)
        embedded_match = self.embedded_pattern.search(link)
        message_link_match = self.message_link_pattern.search(link)
        message_link_ignore_match = self.message_link_ignore_pattern.search(link)
        ignore_match = self.ignore_pattern.search(link)
        public_match = self.public_pattern.search(link)

        if phone_match:
            return TelegramLink.IGNORE
        elif private_match:
            return TelegramLink.PRIVATE
        elif message_link_match:
            return TelegramLink.MESSAGE_LINK
        elif message_link_ignore_match:
            return TelegramLink.IGNORE
        elif instant_view_match:
            return TelegramLink.IGNORE
        elif ignore_match:
            return TelegramLink.IGNORE
        elif public_match:
            return TelegramLink.PUBLIC
        elif embedded_match:
            return TelegramLink.EMBEDDED
        else:
            logger.error(f"Uncaught link pattern: {link}")
            return TelegramLink.UNKNOWN

    async def _join_invite_links(self, invite_links: List[str]) -> None:
        logger.info("Joining invite links")
        for link in tqdm(invite_links):
            start = time.time()

            match self._match_link(link):
                case TelegramLink.PRIVATE:
                    await self.tl_client.join_private_channel(link)
                case TelegramLink.PUBLIC:
                    await self.tl_client.join_public_channel(link)
                case _:
                    logger.error(f"Uncaught link pattern when joining: {link}")
                    pass

            delay = max(CHAT_DELAY - (time.time() - start), 0)
            await asyncio.sleep(delay)

    async def _filter_invite_links(self, invite_links: List[str]) -> List[str]:
        urls = set()
        final_urls = set()

        logger.info("Validating invite links...")

        # First, try and reduce list size by extracting only private and public
        # links and removing duplicates
        for link in invite_links:
            # Remove https?:// substring from string
            link = re.sub("https?:\/\/", "", link)

            # Remove www. substring from string
            link = re.sub("www[.]", "", link)

            match self._match_link(link):
                case TelegramLink.PRIVATE:
                    urls.add(link)
                case TelegramLink.PUBLIC:
                    # TODO: Improve regex to disregard numeric-only ids
                    if link.split("/")[1].isnumeric():
                        continue
                    urls.add(link)
                case TelegramLink.EMBEDDED:
                    link = "/".join(link.split("/")[:2])
                    link = "/".join(link.split("?")[:1])
                    urls.add(link)
                case TelegramLink.MESSAGE_LINK:
                    link = link.split("/")[0] + "/" + link.split("/")[2]
                    urls.add(link)
                case _:
                    pass

        # For a smaller list, use Telegram's API to check if we should join
        for link in tqdm(urls):
            start = time.time()

            match self._match_link(link):
                case TelegramLink.PRIVATE:
                    if await self.tl_client.check_private_link(link=link):
                        final_urls.add(link)
                case TelegramLink.PUBLIC:
                    if await self.tl_client.check_public_link(link=link):
                        final_urls.add(link)
                case _:
                    logger.warning(f"Uncaught link not transformed: {link}")
                    pass

            delay = max(CHAT_DELAY - (time.time() - start), 0)
            await asyncio.sleep(delay)

        return list(final_urls)

    async def _get_twitter_invite_links(self) -> List[str]:
        urls = set()

        logger.info("Getting invite links from twitter")

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

        logger.info("Getting invite links from database")

        messages = self.db.get_messages_with_pattern(pattern="%t.me%")
        for message in messages:
            # Join group returns from re.findall
            urls_to_add = ["".join(url) for url in self.base_pattern.findall(message)]

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
