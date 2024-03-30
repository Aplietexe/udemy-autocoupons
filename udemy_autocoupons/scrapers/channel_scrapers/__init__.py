"""Scrapers for individual channels, to be used by the Telegram scraper."""

from udemy_autocoupons.scrapers.channel_scrapers.channel_scraper import (
    ChannelScraper,
)
from udemy_autocoupons.scrapers.channel_scrapers.generic_scrapers import (
    generic_scrapers,
)

channel_scrapers: tuple[ChannelScraper, ...] = generic_scrapers
