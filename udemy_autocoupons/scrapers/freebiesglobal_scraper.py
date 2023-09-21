"""This module contains the FreebiesGlobalScraper scraper."""
import asyncio
from asyncio import Queue as AsyncQueue
from logging import getLogger
from threading import Event
from typing import TypedDict

from aiohttp import ClientSession
from bs4 import BeautifulSoup, ResultSet, Tag

from udemy_autocoupons.constants import SCRAPER_WAIT
from udemy_autocoupons.request_with_reattempts import request_with_reattempts
from udemy_autocoupons.scrapers.scraper import Scraper
from udemy_autocoupons.scrapers.wordpress_scraper import (
    WordpressScraper,
    WordpressScraperPersistentData,
)


class _PersistentData(TypedDict):
    """The persistent data used by this scraper.

    It contains the persistent data of the WordpressScraper and a list of pending urls.

    """

    wordpress: WordpressScraperPersistentData
    pending: list[str]


class _Post(TypedDict):
    """The type of the post returned by the API. Only used properties are here."""

    date: str
    link: str


_debug = getLogger("debug")
_printer = getLogger("printer")


class FreebiesGlobalScraper(Scraper):
    """Handles freebiesglobal.com scraping."""

    _DOMAIN = "freebiesglobal.com"
    _DEFAULT_DAYS = 3

    def __init__(
        self,
        queue: AsyncQueue[str | None],
        client: ClientSession,
        persistent_data: _PersistentData | None,
        stop_event: Event,
    ) -> None:
        """Stores provided parameters and initializes wordpress scraper.

        Args:
          queue: An async queue where the urls will be added.
          client: An aiohttp client to use.
          persistent_data: The persistent data previously returned.
          stop_event: An event that will be set on an early stop.

        """
        self._queue = queue
        self._client = client
        self._stop_event = stop_event

        self._wordpress_scraper: WordpressScraper[_Post] = WordpressScraper(
            client=client,
            persistent_data=persistent_data["wordpress"]
            if persistent_data
            else None,
            stop_event=stop_event,
            server_time_offset=-2,
            default_days=self._DEFAULT_DAYS,
            domain=self._DOMAIN,
            get_post_value=lambda post: post["link"],
            process_posts=self._scrape_from_posts,
        )

        _debug.debug("Got persistent data %s", persistent_data)

        self._old_pending = (
            persistent_data["pending"] if persistent_data else []
        )

        self._pending: list[str] = []

    async def scrap(self) -> None:
        """Starts scraping urls and sending them to the queue manager."""
        _debug.debug("Start scraping")

        await self._scrape_from_posts(self._old_pending)

        await self._wordpress_scraper.scrape()

    def create_persistent_data(self) -> _PersistentData | None:
        """Returns the persistent data for the next run.

        Returns:
          A dict with the wordpress scraper persistent data and the pending urls.

        """
        new_persistent_data: _PersistentData = {
            "wordpress": self._wordpress_scraper.get_persistent_data(),
            "pending": self._pending,
        }

        _debug.debug("Returning persistent data %s", new_persistent_data)

        return new_persistent_data

    async def _scrape_from_posts(self, urls: list[str]) -> None:
        errored = False
        for url in urls:
            if self._stop_event.is_set() or errored:
                self._pending.append(url)

            _printer.info("freebiesglobal.com: Checking url")

            await asyncio.sleep(SCRAPER_WAIT)

            if await self._scrape_from_post(url) is False:
                errored = True

    async def _scrape_from_post(self, url: str) -> bool:
        """Processes a post url and sends it to the queue manager.

        Args:
          url: The url to process.

        """
        _debug.debug("Processing post %s", url)

        html = await request_with_reattempts(
            url,
            "text",
            self._client,
            self._stop_event,
        )

        if html is None:
            self._pending.append(url)
            return False

        soup = BeautifulSoup(html, "html.parser")

        dealstore_cat = soup.find("a", class_="rh-dealstore-cat")
        expired_notice = soup.find("span", class_="rh-expired-notice")
        udemy_tags: ResultSet[Tag] = soup.find_all(
            "a",
            class_="btn_offer_block",
            href=lambda href: bool(href) and "udemy" in href,
        )

        if (
            dealstore_cat is None
            or dealstore_cat.text.strip() != "Udemy"
            or expired_notice is not None
            or udemy_tags is None
        ):
            _debug.debug(
                "Skipping post %s. dealstore_cat: %s; expired_notice: %s; udemy_tags: %s",
                url,
                dealstore_cat,
                expired_notice,
                udemy_tags,
            )
            return True

        for tag in udemy_tags:
            link = tag.get("href")
            if isinstance(link, str):
                _debug.debug("Sending %s to async queue", link)
                await self._queue.put(link)

        return True
