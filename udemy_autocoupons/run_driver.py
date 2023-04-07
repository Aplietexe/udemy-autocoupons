"""Entry point for the package."""
from __future__ import annotations

from logging import getLogger
from queue import Queue as MtQueue

from udemy_autocoupons.enroller.enroller import Enroller, RunResult
from udemy_autocoupons.enroller.udemy_driver import UdemyDriver
from udemy_autocoupons.udemy_course import CourseWithCoupon


def run_driver(
    mt_queue: MtQueue[CourseWithCoupon | None],
    profile_directory: str,
    user_data_dir: str,
) -> RunResult:
    """Enrolls from the queue.

    Args:
        mt_queue: A multithreading queue to pass to the enroller.
        profile_directory: The directory of the profile to use.
        user_data_dir: The directory with the profile directory.

    """
    driver = UdemyDriver(profile_directory, user_data_dir)

    enroller = Enroller(driver, mt_queue)
    run_result = enroller.enroll_from_queue()

    debug = getLogger("debug")

    debug.debug("Quitting driver")

    driver.quit()

    return run_result
