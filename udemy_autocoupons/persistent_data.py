"""This file contains functions to load and save persistent data."""

from collections import defaultdict
from logging import getLogger
from pathlib import Path
from pickle import Pickler, Unpickler
from typing import Any

from udemy_autocoupons.courses_store import CoursesStore
from udemy_autocoupons.scrapers import ScrapersT
from udemy_autocoupons.thread_safe_list import ThreadSafeList
from udemy_autocoupons.udemy_course import CourseWithCoupon

_debug = getLogger("debug")


def save_scrapers_data(scrapers: ScrapersT) -> None:
    """Saves the scrapers persistent data to a file.

    Args:
        scrapers: The used scrapers.

    """
    scrapers_data = {
        scraper.__class__.__name__: scraper.create_persistent_data()
        for scraper in scrapers
    }

    _save_persistent("scrapers.pickle", scrapers_data)


def load_scrapers_data() -> defaultdict[str, Any]:
    """Loads the scrapers persistent data.

    Returns:
        The persistent data if it can be found, None otherwise. It is adjusted
        to the amount of scrapers by adding None at the end if needed.

    """
    if previous := _load_persistent("scrapers.pickle"):
        return defaultdict(lambda: None, previous)

    return defaultdict(lambda: None)


def save_courses_store(courses_store: CoursesStore) -> None:
    """Saves the courses store to a file.

    Args:
        courses_store: The courses store.

    """
    _save_persistent("courses_store.pickle", courses_store.create_compressed())


def load_courses_store() -> CoursesStore:
    """Loads the courses store.

    Returns:
        The courses store if it can be found, an empty one otherwise.

    """
    courses_store = CoursesStore()

    if compressed := _load_persistent("courses_store.pickle"):
        courses_store.load_compressed(compressed)

    return courses_store


def save_errors(errors: ThreadSafeList[CourseWithCoupon]) -> None:
    """Saves the errors to a file.

    Args:
        errors: The previous errors.

    """
    _save_persistent("errors.pickle", errors.to_list())


def load_errors() -> ThreadSafeList[CourseWithCoupon]:
    """Loads the errors.

    Returns:
        The errors if they can be found, an empty ThreadSafeList otherwise.

    """
    if previous := _load_persistent("errors.pickle"):
        return ThreadSafeList(previous)

    return ThreadSafeList()


def _save_persistent(filename: str, to_persist: Any) -> None:
    """Saves the scrapers persistent data to a file.

    Args:
        filename: The filename to use. Data is always stored in the data dir.
        to_persist: The data to persist.

    """
    path = Path.cwd() / "data" / filename
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    _debug.debug("Saving %s", to_persist)

    with path.open("wb") as pickle_file:
        pickler = Pickler(pickle_file, 4)

        pickler.dump(to_persist)


def _load_persistent(filename: str) -> Any | None:
    """Loads persistent data.

    Args:
        filename: The filename to use. The file is read from the data dir.

    Returns:
        The persistent data if it can be found, None otherwise.

    """
    path = Path.cwd() / "data" / filename
    if not path.is_file():
        _debug.debug("No file found in %s", path)

        return None

    with path.open("rb") as pickle_file:
        pickler = Unpickler(pickle_file)
        previous_persistent_data = pickler.load()

        _debug.debug("Loaded %s", previous_persistent_data)

        return previous_persistent_data
