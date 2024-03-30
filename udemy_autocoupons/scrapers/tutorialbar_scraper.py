"""This module contains the TutorialbarScraper scraper."""

from asyncio import Queue as AsyncQueue
from logging import getLogger
from threading import Event
from typing import TypedDict

from aiohttp import ClientSession

from udemy_autocoupons.scrapers.scraper import Scraper
from udemy_autocoupons.scrapers.wordpress_scraper import (
    WordpressScraper,
    WordpressScraperPersistentData,
)


class _PreviousPersistentData(TypedDict):
    """The persistent data in an old format that will be migrated."""

    last_date: str


class _PersistentData(TypedDict):
    """The persistent data used by this scraper."""

    wordpress: WordpressScraperPersistentData | None


class _AcfT(TypedDict):
    course_url: str


class _Post(TypedDict):
    date: str
    acf: _AcfT


_printer = getLogger("printer")
_debug = getLogger("debug")


class TutorialbarScraper(Scraper):
    """Handles tutorialbar.com scraping."""

    _DOMAIN = "tutorialbar.com"
    _DEFAULT_DAYS = 15

    def __init__(
        self,
        queue: AsyncQueue[str | None],
        client: ClientSession,
        persistent_data: _PersistentData | _PreviousPersistentData | None,
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

        _debug.debug("Got persistent data %s", persistent_data)
        migrated_persistent_data = self._migrate(persistent_data)

        self._wordpress_scraper: WordpressScraper[_Post] = WordpressScraper(
            client=client,
            persistent_data=migrated_persistent_data["wordpress"],
            stop_event=stop_event,
            server_time_offset=-2,
            default_days=self._DEFAULT_DAYS,
            domain=self._DOMAIN,
            get_post_value=lambda post: post["acf"]["course_url"],
            process_posts=self._enqueue_urls,
        )

        self._new_last_date: str | None = None

    async def scrap(self) -> None:
        """Starts scraping urls and sending them to the queue manager."""
        _debug.debug("Start scraping")

        await self._wordpress_scraper.scrape()

    def create_persistent_data(self) -> _PersistentData | None:
        """Returns the persistent data for the next run.

        Returns:
          A dict with the wordpress scraper persistent data.

        """
        new_persistent_data: _PersistentData = {
            "wordpress": self._wordpress_scraper.get_persistent_data(),
        }

        _debug.debug("Returning persistent data %s", new_persistent_data)

        return new_persistent_data

    @staticmethod
    def _migrate(
        persistent_data: _PersistentData | _PreviousPersistentData | None,
    ) -> _PersistentData:
        if not persistent_data:
            return {"wordpress": None}

        if last_date := persistent_data.get("last_date"):
            _printer.info(
                "tutorialbar.com scraper: Migrating persistent data from old format",
            )
            _debug.debug(
                "Migrating persistent data from old format: %s",
                persistent_data,
            )

            return {
                "wordpress": {
                    "last_date": last_date,
                },
            }

        _debug.debug("Persistent data is already in the current format")
        return persistent_data  # type: ignore

    async def _enqueue_urls(self, urls: list[str]) -> None:
        for url in urls:
            if "udemy" in url:
                await self._queue.put(url)
            else:
                _debug.debug("%s is not a udemy url", url)
