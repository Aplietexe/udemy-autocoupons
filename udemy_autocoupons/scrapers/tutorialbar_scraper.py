"""This module contains the TutoralbarScraper scraper."""
import asyncio
from asyncio import Queue as AsyncQueue
from typing import TypedDict

from aiohttp import ClientSession

from udemy_autocoupons.scrapers.scraper import Scraper


class _PersistentData(TypedDict):
    last_date: str


class _AcfT(TypedDict):
    course_url: str


class _PostT(TypedDict):
    date: str
    acf: _AcfT


class TutoralbarScraper(Scraper):
    """Handles tutorialbar.com scraping."""
    _WAIT = 1
    _LONG_WAIT = 5
    _BASE = 'https://www.tutorialbar.com/wp-json/wp/v2/posts?per_page=100&context=embed&order=asc'
    _CODE_OK = 200
    _MAX_ATTEMPTS = 5

    def __init__(
        self,
        queue: AsyncQueue[str | None],
        client: ClientSession,
        persistent_data: _PersistentData | None,
    ) -> None:
        """Stores provided manager, client and persistent data."""
        self._queue = queue
        self._client = client
        self._persistent_data = persistent_data

        self._new_last_date: str | None = None

    async def scrap(self) -> None:
        """Starts scraping courses and sending them to the queue manager."""
        offset = 0

        while courses := await self._request_courses(offset):
            for course in courses:
                await self._queue.put(course)

            if len(courses) != 100:
                break

            await asyncio.sleep(self._WAIT)
            offset += 100

    def create_persistent_data(self) -> _PersistentData | None:
        """Returns the publish date of most recent URL.

        The last_date value is a ISO8601 compliant date that can later be used
        as an API argument.

        Returns:
          A dict with a single last_date key if the run was successful, the
          previous persistent data otherwise.

        """
        return {
            'last_date': self._new_last_date,
        } if self._new_last_date else self._persistent_data

    async def _request_courses(self, offset: int) -> list[str] | None:
        """Sends a request with the given offset.

        It can resend the request several times if it keeps failing.
        When courses are obtained correctly, _new_last_date is updated.

        Args:
            offset: The offset to use for the request.

        Returns:
            A list of up to 100 udemy course urls if the request was successful.
            None otherwise. The returned list could be empty if the offset is
            too high.

        """
        url = f'{self._BASE}&offset={offset}'
        if self._persistent_data:
            after = self._persistent_data['last_date']
            url += f'&after={after}'

        attempts = 0

        while attempts < self._MAX_ATTEMPTS:
            async with self._client.get(url) as res:
                if res.status != self._CODE_OK:
                    attempts += 1
                    await asyncio.sleep(self._LONG_WAIT)
                    continue

                json_res: list[_PostT] = await res.json()

                if json_res:  # pylint: disable=consider-using-assignment-expr
                    self._new_last_date = json_res[-1]['date']

                return [post['acf']['course_url'] for post in json_res]
