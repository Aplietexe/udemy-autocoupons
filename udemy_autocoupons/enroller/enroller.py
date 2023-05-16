"""This module contains the Enroller class."""

from collections import defaultdict, deque
from logging import getLogger
from queue import Queue as MtQueue

from udemy_autocoupons.courses_store import CoursesStore
from udemy_autocoupons.enroller.state import DoneOrErrorT, State
from udemy_autocoupons.enroller.udemy_driver import UdemyDriver
from udemy_autocoupons.udemy_course import CourseWithCoupon

_printer = getLogger("printer")
_debug = getLogger("debug")


class ConsecutiveErrors(Exception):
    """Raised when there are too many consecutive errors."""


class Enroller:
    """A class that handles enrolling from a queue using a WebDriver."""

    _MAX_REATTEMPTS = 2
    _MAX_CONSECUTIVE_ERRORS = 3  # Allowed quantity, next one will raise

    def __init__(
        self,
        driver: UdemyDriver,
        mt_queue: MtQueue,
        courses_store: CoursesStore,
    ) -> None:
        """Stores the given driver and mt_queue.

        Args:
            driver: The WebDriver to use.
            mt_queue: The multithreading queue to get the courses from.
            courses_store: The courses store to use.
            stop_event: The event to set when the run should stop.

        """
        self._driver = driver
        self._mt_queue = mt_queue
        self._courses_store = courses_store

        self._errors: list[CourseWithCoupon] = []

        self._enrolled_counter = 0
        self._consecutive_errors = 0

        self._attempts: defaultdict[CourseWithCoupon, int] = defaultdict(int)
        self._reattempt_queue: deque[CourseWithCoupon] = deque()

    def enroll_from_queue(self) -> list[CourseWithCoupon]:
        """Enrolls in all courses in a queue, retrying if needed.

        When a None is received from the queue, it is considered that there won't be
        any more courses.

        Courses that fail too many times are put in the errors queue.

        """
        try:
            self._enroll_from_queue()
        except ConsecutiveErrors:
            self._errors.extend(self._reattempt_queue)

            while course := self._mt_queue.get():
                self._errors.append(course)
                self._mt_queue.task_done()

            self._mt_queue.task_done()  # For the None

            _printer.info("Too many consecutive errors, stopping early.")
            _debug.debug("Too many consecutive errors, stopping early.")

        self._mt_queue.task_done()  # For the None or the last task that failed

        _debug.debug("Enrolled in %s courses", self._enrolled_counter)
        _printer.info("Enrolled in %s courses", self._enrolled_counter)

        return self._errors

    def _enroll_from_queue(self) -> None:
        """Enrolls in all courses in a queue, retrying if needed.

        When a None is received from the queue, it is considered that there won't be
        any more courses.

        """
        while course := self._mt_queue.get():
            self._handle_enroll(course)
            self._mt_queue.task_done()

        _debug.debug("Got None in multithreading queue")

        while self._reattempt_queue:
            course = self._reattempt_queue.popleft()

            _debug.debug("Reattempting %s", course)
            _printer.info(
                "Enroller: Reattempting courses up to %s times. %s enqueued",
                self._MAX_REATTEMPTS,
                len(self._reattempt_queue),
            )

            self._handle_enroll(course)

    def _handle_enroll(self, course: CourseWithCoupon) -> None:
        if course in self._courses_store:
            _debug.debug("%s is already in store", course)
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

        if state is not State.ERROR:
            self._consecutive_errors = 0
            _printer.info("Enrolled in %s", course.url_id)

        if state in {State.TO_BLACKLIST, State.PAID}:
            _printer.info("Skipping %s", course.url_id)

        if state in {State.ENROLLED, State.TO_BLACKLIST}:
            self._courses_store.add(course.with_any_coupon())
        elif state is State.PAID:
            self._courses_store.add(course)
        # Only case left is ERROR
        else:
            self._handle_error(course)

    def _handle_error(self, course: CourseWithCoupon) -> None:
        self._consecutive_errors += 1

        if self._consecutive_errors > self._MAX_CONSECUTIVE_ERRORS:
            self._errors.append(course)
            raise ConsecutiveErrors()

        if self._attempts[course] < self._MAX_REATTEMPTS:
            self._attempts[course] += 1
            self._reattempt_queue.append(course)
        else:
            self._errors.append(course)
