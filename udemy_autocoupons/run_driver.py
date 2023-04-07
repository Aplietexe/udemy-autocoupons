"""Entry point for the package."""
from __future__ import annotations

from logging import getLogger
from multiprocessing import JoinableQueue as MpQueue

from udemy_autocoupons.enroller.enroller import Enroller, RunResult
from udemy_autocoupons.enroller.udemy_driver import UdemyDriver
from udemy_autocoupons.udemy_course import CourseWithCoupon


def run_driver(
    mp_queue: MpQueue[  # pylint: disable=unsubscriptable-object
        CourseWithCoupon | None
    ],
) -> RunResult:
    """Enrolls from the queue.

    Args:
        mp_queue: A multiprocessing queue to pass to the enroller.


    """
    driver = UdemyDriver()

    enroller = Enroller(driver, mp_queue)
    run_result = enroller.enroll_from_queue()

    debug = getLogger("debug")

    debug.debug("Quitting driver")

    driver.quit()

    return run_result
