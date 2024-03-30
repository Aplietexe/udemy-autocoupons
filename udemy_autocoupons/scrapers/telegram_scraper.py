"""This module contains the TelegramScraper scraper."""

from asyncio import Queue as AsyncQueue, Semaphore, Task, TaskGroup
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from logging import getLogger
from os import getenv
from threading import Event
from typing import Any, TypedDict

from aiohttp import ClientSession
from telethon import TelegramClient
from telethon.tl.custom import Message

from udemy_autocoupons.scrapers.channel_scrapers import (
    ChannelScraper,
    channel_scrapers,
)
from udemy_autocoupons.scrapers.scraper import Scraper

_debug = getLogger("debug")
_printer = getLogger("printer")


class _PersistentData(TypedDict):
    """The persistent data used by this scraper."""

    last_ids: dict[str, int]
    pending_messages: defaultdict[str, set[int]]


class TelegramScraper(Scraper):
    """Handles telegram scraping."""

    _DEFAULT_DAYS = 7

    def __init__(
        self,
        queue: AsyncQueue[str | None],
        client: ClientSession,
        persistent_data: _PersistentData | None,
        stop_event: Event,
    ) -> None:
        """Stores provided parameters.

        Args:
            queue: An async queue where the urls will be added.
            client: An aiohttp client to use.
            persistent_data: The persistent data previously returned.
            stop_event: An event that will be set on an early stop.

        """
        self._queue = queue
        self._aiohttp_client = client
        self._stop_event = stop_event

        api_id_str = getenv("TELEGRAM_API_ID")
        self._api_id = int(api_id_str) if api_id_str else None
        self._api_hash = getenv("TELEGRAM_API_HASH")

        _debug.debug(
            "Got api id %s and api hash %s",
            self._api_id,
            self._api_hash,
        )

        _debug.debug("Got persistent data %s", persistent_data)
        self._last_ids = persistent_data["last_ids"] if persistent_data else {}
        self._pending_messages: defaultdict[str, set[int]] = (
            persistent_data["pending_messages"]
            if persistent_data
            else defaultdict(set)
        )

        max_concurrent_requests = 15  # max per host
        self._semaphores: defaultdict[str, Semaphore] = defaultdict(
            lambda: Semaphore(max_concurrent_requests),
        )

    def create_persistent_data(self) -> _PersistentData | None:
        """Returns the persistent data."""
        persistent_data: _PersistentData = {
            "last_ids": self._last_ids,
            "pending_messages": self._pending_messages,
        }

        _debug.debug("Returning persistent data %s", persistent_data)
        return persistent_data

    async def scrap(self) -> None:
        """Scrapes telegram channels for links."""
        if not await self._is_enabled():
            return

        _debug.debug("Scraping telegram")

        assert self._api_id
        assert self._api_hash

        async with TelegramClient(
            "telegram_session",
            self._api_id,
            self._api_hash,
        ) as client:
            async with TaskGroup() as task_group:
                for channel_scraper in channel_scrapers:
                    task_group.create_task(
                        self._scrap_channel(client, channel_scraper),
                    )

            _debug.debug("Finished scraping telegram")
        _debug.debug("Telegram client disconnected")

    def _get_base_id(
        self,
        channel_id: str,
        message_ids: set[int],
    ) -> int | None:
        """Returns the current id."""
        curr_id = self._last_ids.get(channel_id)
        if curr_id is None and message_ids:
            curr_id = min(message_ids)
        return curr_id

    async def _is_enabled(self) -> bool:
        """Returns whether the scraper is enabled."""
        if not self._api_id or not self._api_hash:
            _debug.warning("TELEGRAM_API_ID or TELEGRAM_API_HASH is not set")
            _printer.info(
                "Telegram scraper is disabled because credentials are not set",
            )
            return False

        client = TelegramClient(
            "telegram_session",
            self._api_id,
            self._api_hash,
        )
        if not client.is_connected():
            _debug.debug("Connecting to Telegram")
            await client.connect()

        if not await client.is_user_authorized():
            _debug.warning("Not logged in to Telegram")
            _printer.warning(
                "Telegram API credentials are set but you are not logged in. Run python -m udemy_autocoupons --setup telegram to log in.",
            )
            client.disconnect()
            return False

        client.disconnect()

        return True

    async def _scrap_channel(
        self,
        client: TelegramClient,
        channel_scraper: ChannelScraper,
    ) -> None:
        """Scrapes a telegram channel for links.

        Args:
            client: The Telegram client to use.
            channel_scraper: The scraper for the channel.

        Returns:
            The number of urls found.
        """
        channel_id = channel_scraper.channel_id
        main_args = {
            "entity": channel_id,
            "reverse": True,
        }

        if min_id := self._last_ids.get(
            channel_id,
        ):
            main_args["min_id"] = min_id
        else:
            main_args["offset_date"] = datetime.now(timezone.utc) - timedelta(
                days=self._DEFAULT_DAYS,
            )

        pending_args = {
            "entity": channel_id,
            "ids": list(self._pending_messages[channel_id]),
            "wait_time": 1,
        }

        _debug.debug(
            "Scraping channel %s with main_args %s and pending_args %s",
            channel_id,
            main_args,
            pending_args,
        )

        tasks: list[Task[int]] = []
        async with TaskGroup() as task_group:
            if self._pending_messages[channel_id]:
                tasks.extend(
                    await self._add_tasks(
                        channel_scraper,
                        task_group,
                        client,
                        pending_args,
                    ),
                )

            tasks.extend(
                await self._add_tasks(
                    channel_scraper,
                    task_group,
                    client,
                    main_args,
                ),
            )

        counter = sum(task.result() for task in tasks)

        _debug.debug(
            "Finished scraping channel %s with %s urls",
            channel_id,
            counter,
        )

        _printer.info(
            "Scraped %s urls from %s telegram channel",
            counter,
            channel_id,
        )

    async def _add_tasks(
        self,
        channel_scraper: ChannelScraper,
        group: TaskGroup,
        client: TelegramClient,
        args: dict[str, Any],
    ) -> list[Task[int]]:
        """Adds tasks to the task group.

        Args:
            channel_scraper: The scraper for the channel.
            group: The task group to add the tasks to.
            client: The Telegram client to use.
            args: The arguments to pass to the iterator.

        Returns:
            The tasks added.

        """
        if self._stop_event.is_set():
            return []

        channel_id = channel_scraper.channel_id
        tasks: list[Task[int]] = []
        async for message in client.iter_messages(**args):
            if self._stop_event.is_set():
                break

            if message is None:
                continue

            assert isinstance(message, Message)

            self._pending_messages[channel_id].add(message.id)
            self._last_ids[channel_id] = max(
                self._last_ids.get(channel_id, 0),
                message.id,
            )

            tasks.append(
                group.create_task(
                    self._scrap_message(
                        message,
                        channel_scraper,
                    ),
                ),
            )

        return tasks

    async def _scrap_message(
        self,
        message: Message,
        channel_scraper: ChannelScraper,
    ) -> int:
        """Scrapes a message for links.

        Args:
            message: The message to scrape.
            channel_scraper: The scraper for the channel.

        Returns:
            The urls found in the message.
        """
        channel_id = channel_scraper.channel_id
        _debug.debug(
            "Processing message %s of %s",
            message.id,
            channel_id,
        )

        urls = await channel_scraper.process_message(
            message,
            self._aiohttp_client,
            self._stop_event,
            self._semaphores,
        )

        _debug.debug(
            "Got %s urls from message %s in %s: %s",
            len(urls),
            message.id,
            channel_id,
            urls,
        )

        if self._stop_event.is_set():
            return 0

        for url in urls:
            await self._queue.put(url)

        self._pending_messages[channel_id].remove(message.id)

        return len(urls)
