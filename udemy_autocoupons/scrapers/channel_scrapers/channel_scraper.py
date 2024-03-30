"""Type definition for channel scrapers."""

from asyncio import Semaphore
from collections import defaultdict
from collections.abc import Awaitable, Callable
from threading import Event
from typing import NamedTuple

from aiohttp import ClientSession
from telethon.tl.custom import Message


class ChannelScraper(NamedTuple):
    """A scraper for a Telegram channel."""

    channel_id: str
    process_message: Callable[
        [Message, ClientSession, Event, defaultdict[str, Semaphore]],
        Awaitable[list[str]],
    ]
