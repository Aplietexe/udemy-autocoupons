"""This file contains functions to load and save persistent data."""

from collections import defaultdict
from logging import getLogger
from pathlib import Path
from pickle import Pickler, Unpickler
from typing import Any

from udemy_autocoupons.scrapers import ScrapersT

scrapers_path = Path.cwd() / 'data' / 'scrapers.pickle'
_debug = getLogger('debug')


def save_scrapers_data(scrapers: ScrapersT) -> None:
    """Saves the scrapers persistent data to a file.

    Args:
        scrapers: The used scrapers.

    """
    if not scrapers_path.is_file():
        scrapers_path.parent.mkdir(parents=True, exist_ok=True)
        scrapers_path.touch()

    scrapers_data = {
        scraper.__class__.__name__: scraper.create_persistent_data()
        for scraper in scrapers
    }

    _debug.debug('Saving %s', scrapers_data)

    with scrapers_path.open('wb') as pickle_file:
        pickler = Pickler(pickle_file, 4)

        pickler.dump(scrapers_data)


def load_scrapers_data() -> defaultdict[str, Any]:
    """Loads the scrapers persistent data.

    Returns:
        The persistent data if it can be found, None otherwise. It is adjusted
        to the amount of scrapers by adding None at the end if needed.

    """
    if not scrapers_path.is_file():
        _debug.debug('No file found in %s', scrapers_path)

        return defaultdict(lambda: None)

    with scrapers_path.open('rb') as pickle_file:
        pickler = Unpickler(pickle_file)
        previous_persistent_data = pickler.load()

        _debug.debug('Loaded %s', previous_persistent_data)

        return defaultdict(lambda: None, previous_persistent_data)


load_scrapers_data()
