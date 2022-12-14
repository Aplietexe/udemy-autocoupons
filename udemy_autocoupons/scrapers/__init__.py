"""This package contains all scrapers."""
from udemy_autocoupons.scrapers.tutorialbar_scraper import TutorialbarScraper

scraper_types = (TutorialbarScraper,)

ScrapersT = tuple[TutorialbarScraper]
