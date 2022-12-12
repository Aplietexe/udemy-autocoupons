"""This module contains the TutoralbarScraper scraper."""
import asyncio
from asyncio import Queue as AsyncQueue
from logging import getLogger
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


_printer = getLogger('printer')
_debug = getLogger('debug')


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
        """Stores provided manager, client and persistent data.

        Args:
          queue: An async queue where the urls will be added.
          client: An aiohttp client to use.
          persistent_data: The persistent data previously returned.

        """
        self._queue = queue
        self._client = client
        self._persistent_data = persistent_data
        _debug.debug('Loaded persistent data %s', persistent_data)

        self._new_last_date: str | None = None

    async def scrap(self) -> None:
        """Starts scraping urls and sending them to the queue manager."""
        _debug.debug('Start scraping')
        offset = 0

        while urls := await self._request(offset):
            _printer.info('Got %s urls from tutorialbar.com.', len(urls))
            _debug.debug('Sending %s urls to async queue', len(urls))

            for url in urls:
                if 'udemy' in url:
                    await self._queue.put(url)
                else:
                    _debug.debug('%s is not a udemy url', url)

            if len(urls) != 100:
                _debug.debug(
                    'Stopping scraper because only %s urls were received',
                    len(urls),
                )
                break

            await asyncio.sleep(self._WAIT)
            offset += 100
        _debug.debug('Finishing scraper, last urls value was %s', urls)

    def create_persistent_data(self) -> _PersistentData | None:
        """Returns the publish date of most recent URL.

        The last_date value is a ISO8601 compliant date that can later be used
        as an API argument.

        Returns:
          A dict with a single last_date key if the run was successful, the
          previous persistent data otherwise.

        """
        persistent_data: _PersistentData | None = {
            'last_date': self._new_last_date,
        } if self._new_last_date else None

        _debug.debug(
            'Returning persistent data %s because self._new_last_date is %s',
            persistent_data,
            self._new_last_date,
        )

        return persistent_data

    async def _request(self, offset: int) -> list[str] | None:
        """Sends a request with the given offset.

        It can resend the request several times if it keeps failing.
        When urls are obtained correctly, _new_last_date is updated.

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

        _debug.debug('Sending request to %s', url)

        attempts = 0

        while attempts < self._MAX_ATTEMPTS:
            async with self._client.get(url) as res:
                if res.status != self._CODE_OK:
                    _debug.debug(
                        'Got code %s from %s. attempts == %s. Reattempting in %s',
                        res.status,
                        url,
                        attempts,
                        self._LONG_WAIT,
                    )

                    attempts += 1
                    await asyncio.sleep(self._LONG_WAIT)
                    continue

                json_res: list[_PostT] = await res.json()

                if json_res:  # pylint: disable=consider-using-assignment-expr
                    self._new_last_date = json_res[-1]['date']
                    _debug.debug(
                        'Reassigning self._new_last_date to %s',
                        self._new_last_date,
                    )

                urls = None

                try:
                    urls = [post['acf']['course_url'] for post in json_res]
                except (KeyError, TypeError):
                    _debug.exception(
                        'JSON response does not follow the expected format. Response was %s',
                        json_res,
                    )
                    _printer.error(
                        'Error extracting course urls from tutorialbar. Check logs.',
                    )

                return urls
