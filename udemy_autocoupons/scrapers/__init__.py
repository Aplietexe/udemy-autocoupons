"""This package contains all scrapers."""
from udemy_autocoupons.scrapers.freebiesglobal_scraper import (
    FreebiesGlobalScraper,
)
from udemy_autocoupons.scrapers.tutorialbar_scraper import TutorialbarScraper

scraper_types = (TutorialbarScraper, FreebiesGlobalScraper)

ScrapersT = tuple[TutorialbarScraper, FreebiesGlobalScraper]
