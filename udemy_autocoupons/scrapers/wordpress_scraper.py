"""This module contains the TutorialbarScraper scraper."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from logging import getLogger
from threading import Event
from typing import Generic, TypedDict, TypeVar

from aiohttp import ClientSession

from udemy_autocoupons.constants import SCRAPER_WAIT
from udemy_autocoupons.request_with_reattempts import request_with_reattempts


class WordpressPost(TypedDict):
    """The type of the post returned by the API. Only used properties are here."""

    date: str


_Post = TypeVar("_Post", bound=WordpressPost)


class WordpressScraperPersistentData(TypedDict):
    """The persistent data used by this scraper.

    last_date is an ISO8601 compliant date (with precision up to the second)
    that can later be used as an API argument.

    """

    last_date: str


_printer = getLogger("printer")
_debug = getLogger("debug")


class WordpressScraper(Generic[_Post]):
    """Handles tutorialbar.com scraping."""

    def __init__(
        self,
        client: ClientSession,
        persistent_data: WordpressScraperPersistentData | None,
        stop_event: Event,
        server_time_offset: float,
        default_days: int,
        domain: str,
        get_post_value: Callable[[_Post], str],
        process_posts: Callable[[list[str]], Awaitable[None]],
    ) -> None:
        """Stores provided parameters and generates a default last_date if needed.

        Args:
          client: An aiohttp client to use.
          persistent_data: The persistent data from the previous run.
          stop_event: An event that will be set on an early stop.
          server_time_offset: The timezone offset between the server and UTC.
          default_days: The number of days before current time to use for the default last_date.
          domain: The domain of the site, without protocol.
          get_post_value: A function that will be called to safely extract a value from the post.
          process_posts: A function that will be called for each batch of posts with the extracted post values.

        """
        self._client = client
        self._stop_event = stop_event
        self._domain = domain
        self._get_post_value = get_post_value
        self._process_posts = process_posts

        _debug.debug("%s: Got last_date %s", self._domain, persistent_data)

        default_last_date = datetime.now(
            timezone(timedelta(hours=server_time_offset)),
        ) - timedelta(days=default_days)

        self._last_date = (
            persistent_data["last_date"]
            if persistent_data
            else default_last_date.strftime(
                "%Y-%m-%dT%H:%M:%S",
            )
        )

        self._new_last_date: str | None = None

    async def scrape(self) -> None:
        """Starts scraping post urls and sending them to the processing function."""
        _debug.debug("%s: Started scraping", self._domain)
        offset = 0

        while urls := await self._request(self._generate_url(offset)):
            _printer.info(
                "%s: Got %s urls. Filtering them...",
                self._domain,
                len(urls),
            )
            _debug.debug(
                "%s: Sending %s urls to processing",
                self._domain,
                len(urls),
            )

            await self._process_posts(urls)

            if len(urls) != 100:
                _debug.debug(
                    "%s: Stopping scraper because only %s urls were received",
                    self._domain,
                    len(urls),
                )
                break

            await asyncio.sleep(SCRAPER_WAIT)
            offset += 100
        _debug.debug(
            "%s: Finishing scraper, last urls value was %s",
            self._domain,
            urls,
        )

    def get_persistent_data(  # noqa: WPS615
        self,
    ) -> WordpressScraperPersistentData:
        """Returns the persistent data for the next run.

        This method should be called after the scraper has finished.

        Returns:
            A dict with the new last date if it was set, the old one otherwise.
            It is an ISO8601 compliant date with precision up to the second.

        """
        persistent_data: WordpressScraperPersistentData = {
            "last_date": self._new_last_date or self._last_date,
        }
        _debug.debug(
            "%s: Returning persistent data %s",
            self._domain,
            persistent_data,
        )
        return persistent_data

    async def _request(self, url: str) -> list[str] | None:
        """Sends a request to the given url.

        It can resend the request several times if it keeps failing.

        Args:
            url: The url to send the request to.

        Returns:
            A list of up to 100 post values if the request was successful.
            None otherwise.

        """
        json_res: list[_Post] | None = await request_with_reattempts(
            url,
            "json",
            self._client,
            self._stop_event,
        )

        if not json_res:
            return None

        return self._process_json(json_res)

    def _process_json(self, json_res: list[_Post]) -> list[str] | None:
        """Validates and processes the json response.

        Args:
            json_res: The json response.

        Returns:
            A list of up to 100 urls if the provided response is valid.
            None otherwise.

        """
        urls = None

        try:
            urls = self._extract_values_from_posts(json_res)
        except (KeyError, TypeError):
            _debug.exception(
                "%s: JSON response does not follow the expected format. Response was %s",
                self._domain,
                json_res,
            )
            _printer.error(
                "ERROR extracting course urls from %s. Check logs.",
                self._domain,
            )

        return urls

    def _extract_values_from_posts(self, json_res: list[_Post]) -> list[str]:
        """Extracts the post values from the json response and updates _new_last_date.

        Args:
            json_res: The json response.

        Returns:
            A list of post values extracted from the json response with process_posts.

        """
        if urls := [self._get_post_value(post) for post in json_res]:
            self._new_last_date = json_res[-1]["date"]
            _debug.debug(
                "%s: Reassigning self._new_last_date to %s",
                self._domain,
                self._new_last_date,
            )

        return urls

    def _generate_url(self, offset: int) -> str:
        """Generates a url with the given offset and other required parameters.

        Args:
            offset: The offset to use.

        Returns:
            A url with the given offset.

        """
        url = f"https://www.{self._domain}/wp-json/wp/v2/posts?per_page=100&context=embed&order=asc&offset={offset}&after={self._last_date}"
        _debug.debug("Generated URL %s", url)
        return url
