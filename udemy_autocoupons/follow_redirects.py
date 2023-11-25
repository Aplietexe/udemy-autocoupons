"""This module provides a function to follow redirects."""
from asyncio import Semaphore, sleep
from logging import getLogger
from threading import Event

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout
from bs4 import BeautifulSoup

_debug = getLogger("debug")

timeout = ClientTimeout(total=10)


async def _handle_y7u2_top(res: ClientResponse) -> str:
    """Handles y7u2.top urls.

    Args:
      url: The url to handle.

    Returns:
      The handled url.
    """
    _debug.debug("Handling %s", res.url)

    html = await res.text()
    soup = BeautifulSoup(html, "html.parser")
    if (span := soup.find("span", id="url")) is None:
        return str(res.url)

    return span.text.strip()


handlers = [("y7u2.top", _handle_y7u2_top)]

_MAX_ATTEMPTS = 7
_WAIT = 2


async def follow_redirects(
    url: str,
    client: ClientSession,
    semaphore: Semaphore,
    stop_event: Event,
) -> str | None:
    """Follows redirects until a non-redirect url is reached.

    Args:
      url: The url to follow redirects from.
      client: An aiohttp client to use.
      semaphore: A semaphore to limit the number of concurrent requests.
      stop_event: An event that will be set on an early stop.

    Returns:
      The non-redirect url.
    """
    async with semaphore:
        for attempt in range(_MAX_ATTEMPTS):
            if stop_event.is_set():
                _debug.debug("Stopping request to %s", url)
                return None
            try:
                return await _follow_redirects(url, client)
            except (ClientError, AssertionError):
                _debug.exception("Error requesting %s", url)
                return None
            except TimeoutError:
                _debug.exception(
                    "Error on requesting %s. attempt: %s",
                    url,
                    attempt,
                )
                await sleep(_WAIT * attempt)


async def _follow_redirects(
    url: str,
    client: ClientSession,
) -> str:
    _debug.debug("Requesting %s", url)
    headers = {"User-Agent": ""}
    final = False
    while not final:
        async with client.get(
            url,
            timeout=timeout,
            headers=headers,
        ) as response:
            final = True
            url = str(response.url)
            for pattern, handle_url in handlers:
                if pattern in url:
                    final = False
                    url = await handle_url(response)
                    break

    return url
