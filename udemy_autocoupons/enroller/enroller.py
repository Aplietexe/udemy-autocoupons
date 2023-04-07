"""This module contains the Enroller class."""

from collections import defaultdict, deque
from logging import getLogger
from queue import Queue as MtQueue
from typing import NamedTuple

from udemy_autocoupons.courses_store import CoursesStore
from udemy_autocoupons.enroller.state import DoneOrErrorT, State
from udemy_autocoupons.enroller.udemy_driver import UdemyDriver
from udemy_autocoupons.udemy_course import CourseWithCoupon

_printer = getLogger("printer")
_debug = getLogger("debug")


class RunResult(NamedTuple):
    """The result of the enroll_from_queue run."""

    blacklist: CoursesStore
    errors: set[CourseWithCoupon]


class Enroller:
    """A class that handles enrolling from a queue using a WebDriver."""

    _MAX_REATTEMPTS = 2

    def __init__(
        self,
        driver: UdemyDriver,
        mt_queue: MtQueue,
    ) -> None:
        """Stores the given driver and mt_queue.

        Args:
            driver: The WebDriver to use.
            mt_queue: The multithreading queue to get the courses from.

        """
        self._driver = driver
        self._mt_queue = mt_queue

        self._blacklist = CoursesStore()
        self._errors: set[CourseWithCoupon] = set()

        self._enrolled_counter = 0

        self._attempts: defaultdict[CourseWithCoupon, int] = defaultdict(int)
        self._reattempt_queue: deque[CourseWithCoupon] = deque()

    def enroll_from_queue(self) -> RunResult:
        """Enrolls in all courses in a queue, retrying if needed.

        When a None is received from the queue, it is considered that there won't be
        any more courses.

        Returns:
            The courses whose coupon doesn't work, the courses to blacklist for
            the next run for whatever reason and the courses that triggered an
            error.

        """
        while course := self._mt_queue.get():
            self._handle_enroll(course)
            _printer.info(
                "Enroller: Approximately %s courses left.",
                self._mt_queue.qsize() - 1,
            )
            self._mt_queue.task_done()

        _debug.debug("Got None in multithreading queue")
        self._mt_queue.task_done()

        while self._reattempt_queue:
            course = self._reattempt_queue.popleft()

            _debug.debug("Reattempting %s", course)
            _printer.info(
                "Enroller: Reattempting courses up to %s times. %s enqueued",
                self._MAX_REATTEMPTS,
                len(self._reattempt_queue),
            )

            self._handle_enroll(course)

        run_result = RunResult(
            self._blacklist,
            self._errors,
        )
        _debug.debug("Run result was %s", run_result)

        _debug.debug("Enrolled in %s courses", self._enrolled_counter)
        _printer.info("Enrolled in %s courses", self._enrolled_counter)

        return run_result

    def _handle_enroll(self, course: CourseWithCoupon) -> None:
        if course in self._blacklist:
            _debug.debug("%s is blacklisted", course)
        else:
            state = self._driver.enroll(course)
            self._handle_state(course, state)

            _debug.debug("Enroll finished for %s", course)

        _debug.debug(
            "mt qsize is %s, reattempt queue size is %s",
            self._mt_queue.qsize(),
            len(self._reattempt_queue),
        )

    def _handle_state(
        self,
        course: CourseWithCoupon,
        state: DoneOrErrorT,
    ) -> None:
        if state is State.ENROLLED:
            self._enrolled_counter += 1

        if state in {State.ENROLLED, State.TO_BLACKLIST}:
            self._blacklist.add(course.with_any_coupon())
        elif state is State.PAID:
            self._blacklist.add(course)
        # Only case left is ERROR
        elif self._attempts[course] < self._MAX_REATTEMPTS:
            self._attempts[course] += 1
            self._reattempt_queue.append(course)
        else:
            self._errors.add(course)
