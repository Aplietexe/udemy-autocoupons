"""Entry point for the package."""

from __future__ import annotations

import os
from logging import getLogger
from queue import Queue as MtQueue
from threading import Event

from udemy_autocoupons.courses_store import CoursesStore
from udemy_autocoupons.enroller.enroller import Enroller
from udemy_autocoupons.enroller.udemy_driver import UdemyDriver
from udemy_autocoupons.udemy_course import CourseWithCoupon


def run_driver(
    mt_queue: MtQueue[CourseWithCoupon | None],
    courses_store: CoursesStore,
    errors: MtQueue[CourseWithCoupon],
    stop_event: Event,
    profile_directory: str,
    user_data_dir: str,
) -> None:
    """Enrolls from the queue.

    Args:
        mt_queue: A multithreading queue to pass to the enroller.
        courses_store: A multithreading queue to pass to the enroller.
        errors: A list to append the errors to.
        stop_event: The event to set when the run should stop.
        profile_directory: The directory of the profile to use.
        user_data_dir: The directory with the profile directory.

    """
    debug = getLogger("debug")
    printer = getLogger("printer")
    try:
        _run_driver(
            mt_queue,
            courses_store,
            errors,
            stop_event,
            profile_directory,
            user_data_dir,
        )
    except:  # noqa: B001
        debug.exception("Error in run_driver")
        printer.error("Error caught, quitting")
        os._exit(1)


def _run_driver(
    mt_queue: MtQueue[CourseWithCoupon | None],
    courses_store: CoursesStore,
    errors: MtQueue[CourseWithCoupon],
    stop_event: Event,
    profile_directory: str,
    user_data_dir: str,
) -> None:
    """Enrolls from the queue.

    Args:
        mt_queue: A multithreading queue to pass to the enroller.
        courses_store: A multithreading queue to pass to the enroller.
        errors: A list to append the errors to.
        stop_event: The event to set when the run should stop.
        profile_directory: The directory of the profile to use.
        user_data_dir: The directory with the profile directory.

    """
    debug = getLogger("debug")

    driver = UdemyDriver(profile_directory, user_data_dir)

    enroller = Enroller(driver, mt_queue, courses_store, stop_event)
    new_errors = enroller.enroll_from_queue()
    for error in new_errors:
        errors.put(error)

    debug.debug("Finished enrolling. Errors: %s", new_errors)

    debug.debug("Quitting driver")

    driver.quit()

    if not stop_event.is_set():
        stop_event.set()
