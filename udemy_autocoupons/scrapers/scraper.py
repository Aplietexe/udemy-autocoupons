"""This module contains the Scraper protocol."""

from typing import Protocol

from aiohttp import ClientSession

from udemy_autocoupons.queue_manager import QueueManager


class Scraper(Protocol):
    """All scrapers have to implement this protocol."""

    def __init__(self, manager: QueueManager, client: ClientSession) -> None:
        """The initialization should have no side effects.

        Args:
          manager: The queue manager that the scraper should use.
          client: The aiohttp client that the scraper should use.

        """

    def start(self) -> None:
        """The scraper should start only when this method is called."""
