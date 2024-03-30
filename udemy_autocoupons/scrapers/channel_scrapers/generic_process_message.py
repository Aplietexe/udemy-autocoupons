"""Scraper for the iDownloadCoupon channel."""

import re
from asyncio import Semaphore, Task, TaskGroup
from collections import defaultdict
from logging import getLogger
from threading import Event

from aiohttp import ClientSession
from telethon.tl.custom import Message
from urlextract import URLExtract
from yarl import URL

from udemy_autocoupons.follow_redirects import follow_redirects

_debug = getLogger("debug")


async def generic_process_message(
    message: Message,
    session: ClientSession,
    stop_event: Event,
    semaphores: defaultdict[str, Semaphore],
) -> list[str]:
    """Process a message from the channel.

    Args:
        message: The message to process.
        session: The aiohttp session to use for requests
        stop_event: An event that will be set on an early stop.
        semaphores: Semaphores to use for limiting the number of concurrent requests.

    Returns:
        A list of urls found in the message.
    """
    _debug.debug("Got message %s", message.id)
    if (message.message) is None:
        return []

    raw_urls = get_urls_from_text(message) + get_urls_from_buttons(message)

    tasks: list[Task[str | None]] = []
    async with TaskGroup() as group:
        for raw_url in raw_urls:
            if stop_event.is_set():
                return []

            tasks.append(
                group.create_task(
                    _fix_url(raw_url, session, stop_event, semaphores),
                ),
            )

    urls = []
    for task in tasks:
        if url := task.result():
            urls.append(url)

    return urls


_BLACKLIST = (
    "https://leveryth.com",
    "https://en.leveryth.com",
    "https://www.tutorialbar.com",
    "https://www.discudemy.com",
    "https://www.reddit.com",
    "https://cursotecaplus.com",
    "https://blog.facialix.com",
    "https://te.me/",
    "https://www.twitter.com",
    "http://exe.io",  # url shortener
    "https://imini.in",
    "https://www.youtube.com",
    "https://youtu.be",
    "https://www.domestika.org",
    "https://www.linkvertise.com",  # url shortener
    "http://q.gs",  # url shortener
    "http://pheecith.com",  # url shortener
    "https://mega.nz",
    "https://www.shine.com",
    "https://www.crehana.com",
    "https://www.freewebcart.com",
    "https://theprogrammingbuddy.club",
)


async def _fix_url(
    url: str,
    session: ClientSession,
    stop_event: Event,
    semaphores: defaultdict[str, Semaphore],
) -> str | None:
    """Fix a url.

    Args:
        url (str): The url to fix.
        session: The aiohttp session to use for requests
        semaphores: Semaphores to use for limiting the number of concurrent requests.

    Returns:
        The fixed url.
    """
    if url.startswith(_BLACKLIST):
        return None

    if url.startswith(("https://www.udemy.com", "https://udemy.com")):
        return url

    host = URL(url).host
    assert host
    new_url = await follow_redirects(url, session, semaphores[host], stop_event)
    _debug.debug("%s redirects to %s", url, new_url)
    return new_url


def get_urls_from_buttons(message: Message) -> list[str]:
    """Get urls from buttons in a message.

    Args:
        message (Message): The message to get urls from.

    Returns:
        A list of urls.
    """
    if not message.buttons:
        return []

    urls = []
    for button_group in message.buttons:
        for button in button_group:
            if button.url:
                urls.append(button.url)

    return urls


_pattern = re.compile("(?=https://)")


def get_urls_from_text(message: Message) -> list[str]:
    """Get urls from text in a message.

    Args:
        message (Message): The message to get urls from.

    Returns:
        A list of urls.
    """
    if not message.raw_text:
        return []

    extractor = URLExtract()
    raw_urls: list[str] = extractor.find_urls(message.raw_text)  # type: ignore
    urls = []
    for url in raw_urls:
        host = URL(url).raw_host
        if url.endswith(".jpg") or not host:
            continue

        new_url = _normalize_scheme(url)
        if "udemy.com" in host:
            new_urls = _pattern.split(new_url)
            new_urls.pop(0)
            urls.extend(_normalize_scheme(url) for url in new_urls)
            continue

        urls.append(new_url)

    return urls


def _normalize_scheme(url: str) -> str:
    """Normalizes the scheme of a url.

    Args:
        url: The url to normalize.

    Returns:
        The normalized url.
    """
    return str(URL(url).with_scheme("https"))
