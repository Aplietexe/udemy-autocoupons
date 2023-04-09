"""Entry point for the package."""
from __future__ import annotations

import os
from logging import getLogger
from queue import Queue as MtQueue

from udemy_autocoupons.courses_store import CoursesStore
from udemy_autocoupons.enroller.enroller import Enroller
from udemy_autocoupons.enroller.udemy_driver import UdemyDriver
from udemy_autocoupons.udemy_course import CourseWithCoupon


def run_driver(
    mt_queue: MtQueue[CourseWithCoupon | None],
    courses_store: CoursesStore,
    profile_directory: str,
    user_data_dir: str,
) -> None:
    """Enrolls from the queue.

    Args:
        mt_queue: A multithreading queue to pass to the enroller.
        courses_store: A multithreading queue to pass to the enroller.
        profile_directory: The directory of the profile to use.
        user_data_dir: The directory with the profile directory.

    """
    debug = getLogger("debug")
    printer = getLogger("printer")
    try:
        _run_driver(mt_queue, courses_store, profile_directory, user_data_dir)
    except:  # noqa: B001
        debug.exception("Error in run_driver")
        printer.error("Error caught, quitting")
        os._exit(1)


def _run_driver(
    mt_queue: MtQueue[CourseWithCoupon | None],
    courses_store: CoursesStore,
    profile_directory: str,
    user_data_dir: str,
) -> None:
    """Enrolls from the queue.

    Args:
        mt_queue: A multithreading queue to pass to the enroller.
        courses_store: A multithreading queue to pass to the enroller.
        profile_directory: The directory of the profile to use.
        user_data_dir: The directory with the profile directory.

    """
    driver = UdemyDriver(profile_directory, user_data_dir)

    enroller = Enroller(driver, mt_queue, courses_store)
    enroller.enroll_from_queue()

    debug = getLogger("debug")

    debug.debug("Quitting driver")

    driver.quit()
