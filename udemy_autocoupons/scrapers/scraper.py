"""This module contains the Scraper Abstract Base Class."""

from abc import ABC, abstractmethod
from asyncio import Queue as AsyncQueue
from threading import Event
from typing import Generic, TypeVar

from aiohttp import ClientSession

_PersistentT = TypeVar("_PersistentT")


class Scraper(ABC, Generic[_PersistentT]):
    """Scrapers have to inherit from this ABC."""

    @abstractmethod
    def __init__(
        self,
        queue: AsyncQueue,
        client: ClientSession,
        persistent_data: _PersistentT | None,
        stop_event: Event,
    ) -> None:
        """The initialization should have no side effects.

        When stop_event is set, the scraper should stop as soon as possible.

        Args:
          queue: The async queue where the scraped urls should be added.
          client: The aiohttp client that the scraper should use.
          persistent_data: Persistent data previously returned by the scraper.
          stop_event: An event that will be set on an early stop.

        """

    @abstractmethod
    async def scrap(self) -> None:
        """The scraper should start only when this method is called."""

    @abstractmethod
    def create_persistent_data(self) -> _PersistentT | None:
        """The return value will be stored after a successful run.

        Returns:
          None if there's no data to store, the data otherwise.

        """
