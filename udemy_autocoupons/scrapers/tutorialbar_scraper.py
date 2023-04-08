"""This module contains the TutorialbarScraper scraper."""
import asyncio
from asyncio import Queue as AsyncQueue
from datetime import datetime, timedelta
from logging import getLogger
from threading import Event
from typing import TypedDict
from zoneinfo import ZoneInfo

from aiohttp import ClientSession

from udemy_autocoupons.scrapers.scraper import Scraper


class _PersistentData(TypedDict):
    """The persistent data used by this scraper.

    last_date is an ISO8601 compliant date (with precision up to the second)
    that can later be used as an API argument.

    """

    last_date: str


class _AcfT(TypedDict):
    course_url: str


class _PostT(TypedDict):
    date: str
    acf: _AcfT


_printer = getLogger("printer")
_debug = getLogger("debug")


class TutorialbarScraper(Scraper):
    """Handles tutorialbar.com scraping."""

    _WAIT = 1
    _LONG_WAIT = 5
    _BASE = "https://www.tutorialbar.com/wp-json/wp/v2/posts?per_page=100&context=embed&order=asc"
    _CODE_OK = 200
    _MAX_ATTEMPTS = 5
    _DEFAULT_DAYS = 15

    def __init__(
        self,
        queue: AsyncQueue[str | None],
        client: ClientSession,
        persistent_data: _PersistentData | None,
        stop_event: Event,
    ) -> None:
        """Stores provided manager, client and persistent data.

        Args:
          queue: An async queue where the urls will be added.
          client: An aiohttp client to use.
          persistent_data: The persistent data previously returned.
          stop_event: An event that will be set on an early stop.

        """
        self._queue = queue
        self._client = client
        self._stop_event = stop_event

        default_last_date = datetime.now(
            ZoneInfo("Asia/Kolkata"),  # Server timezone
        ) - timedelta(days=self._DEFAULT_DAYS)
        self._persistent_data = persistent_data or {
            "last_date": default_last_date.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        _debug.debug("Got persistent data %s", persistent_data)

        self._new_last_date: str | None = None

    async def scrap(self) -> None:
        """Starts scraping urls and sending them to the queue manager."""
        _debug.debug("Start scraping")
        offset = 0

        while urls := await self._request(self._generate_url(offset)):
            _printer.info("Tutorialbar Scraper: Got %s course urls.", len(urls))
            _debug.debug("Sending %s urls to async queue", len(urls))

            await self._enqueue_urls(urls)

            if len(urls) != 100:
                _debug.debug(
                    "Stopping scraper because only %s urls were received",
                    len(urls),
                )
                break

            await asyncio.sleep(self._WAIT)
            offset += 100
        _debug.debug("Finishing scraper, last urls value was %s", urls)

    def create_persistent_data(self) -> _PersistentData | None:
        """Returns the publish date of most recent URL.

        Returns:
          A dict with a single last_date key if the run was successful, the
          previous persistent data otherwise.

        """
        if self._new_last_date:
            persistent_data: _PersistentData = {
                "last_date": self._new_last_date,
            }
            _debug.debug("Returning new persistent data %s", persistent_data)

            return persistent_data

        _debug.debug(
            "Returning old persistent data %s",
            self._persistent_data,
        )

        return self._persistent_data

    async def _request(self, url: str) -> list[str] | None:
        """Sends a request with the given offset.

        It can resend the request several times if it keeps failing.
        When urls are obtained correctly, _new_last_date is updated.

        Args:
            url: The url to send the request to.

        Returns:
            A list of up to 100 udemy course urls if the request was successful.
            None otherwise. The returned list could be empty if the offset is
            too high.

        """
        attempts = 0

        while attempts < self._MAX_ATTEMPTS:
            async with self._client.get(url) as res:
                if res.status != self._CODE_OK:
                    _debug.debug(
                        "Got code %s from %s. attempts == %s. Reattempting in %s",
                        res.status,
                        url,
                        attempts,
                        self._LONG_WAIT,
                    )

                    attempts += 1
                    await asyncio.sleep(self._LONG_WAIT)
                    continue

                json_res: list[_PostT] = await res.json()

            return self._process_json(json_res)

    def _process_json(self, json_res: list[_PostT]) -> list[str] | None:
        urls = None

        try:
            urls = [post["acf"]["course_url"] for post in json_res]
        except (KeyError, TypeError):
            _debug.exception(
                "JSON response does not follow the expected format. Response was %s",
                json_res,
            )
            _printer.error(
                "ERROR extracting course urls from tutorialbar. Check logs.",
            )

        if urls:
            self._new_last_date = json_res[-1]["date"]
            _debug.debug(
                "Reassigning self._new_last_date to %s",
                self._new_last_date,
            )

        return urls

    async def _enqueue_urls(self, urls: list[str]) -> None:
        for url in urls:
            if "udemy" in url:
                await self._queue.put(url)
            else:
                _debug.debug("%s is not a udemy url", url)

    def _generate_url(self, offset: int) -> str:
        url = f"{self._BASE}&offset={offset}"

        if self._persistent_data:
            after = self._persistent_data["last_date"]
            url += f"&after={after}"

        _debug.debug("Sending request to %s", url)

        return url
