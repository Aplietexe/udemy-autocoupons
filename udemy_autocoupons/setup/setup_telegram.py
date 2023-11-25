"""Telegram setup module."""

from logging import getLogger
from os import getenv

from telethon import TelegramClient

_printer = getLogger("printer")
_debug = getLogger("debug")


async def setup_telegram() -> None:
    """Runs telegram login."""
    _debug.debug("Setting up Telegram")

    api_id_str = getenv("TELEGRAM_API_ID")
    api_hash = getenv("TELEGRAM_API_HASH")

    if not api_id_str or not api_hash:
        _debug.error("TELEGRAM_API_ID or TELEGRAM_API_HASH is not set")
        _printer.error("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env")
        return

    api_id = int(api_id_str)

    async with TelegramClient("telegram_session", api_id, api_hash):
        _debug.debug("Telegram client created")

    _debug.debug("Setup complete")
    _printer.info("Logged in to Telegram")
