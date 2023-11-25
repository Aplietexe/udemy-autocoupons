"""Scrapers for individual channels, to be used by the Telegram scraper."""
from udemy_autocoupons.scrapers.channel_scrapers.channel_scraper import (
    ChannelScraper,
)

channel_scrapers: tuple[ChannelScraper, ...] = ()
