"""Miscellaneous utility functions."""

from asyncio import sleep
from logging import getLogger
from threading import Event
from typing import Any, Literal

from aiohttp import ClientError, ClientSession

_debug = getLogger("debug")


class BadStatusCodeError(Exception):
    """Raised when a request returns a bad status code."""

    def __init__(self, status_code: int) -> None:
        """Stores the status code."""
        super().__init__(f"Bad status code: {status_code}")
        self.status_code = status_code


async def request_with_reattempts(
    url: str,
    content_type: Literal["json", "text"],
    client: ClientSession,
    stop_event: Event,
    max_attempts: int = 5,
    wait: int = 5,
) -> Any | None:
    """Sends a request to the given url.

    It can resend the request several times if it keeps failing.

    Args:
        url: The url to send the request to.
        content_type: The type of the response content.
        client: The aiohttp client to use.
        stop_event: An event that will be set on an early stop.
        max_attempts: The maximum number of attempts to make.
        wait: The time to wait between attempts.

    Returns:
        The json response if the request was successful.
        None otherwise.

    """
    attempts = 0

    while attempts < max_attempts:
        if stop_event.is_set():
            _debug.debug("Stopping request to %s", url)
            return None

        _debug.debug("Waiting request to %s", url)

        try:
            res_body = await _send_req(url, content_type, client)
        except (ClientError, BadStatusCodeError):
            _debug.exception("Error requesting %s. attempts: %s", url, attempts)

            attempts += 1
            await sleep(wait)
            continue

        return res_body

    _debug.debug("Max attempts reached for %s", url)
    return None


async def _send_req(
    url: str,
    content_type: Literal["json", "text"],
    client: ClientSession,
) -> Any:
    """Sends a request to the given url.

    Args:
        url: The url to send the request to.
        content_type: The type of the response content.
        client: The aiohttp client to use.

    Returns:
        The json response if the request was successful.

    Raises:
        ClientError: If the request fails.
        BadStatusCodeError: If the request returns a bad status code.

    """
    async with client.get(url) as res:
        if not res.ok:
            _debug.debug("Got code %s from %s", res.status, url)
            raise BadStatusCodeError(res.status)

        res_body = await (res.json() if content_type == "json" else res.text())

    return res_body
