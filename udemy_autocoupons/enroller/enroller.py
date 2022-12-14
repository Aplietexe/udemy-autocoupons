"""This module contains the enroll_from_queue function."""

from collections import defaultdict
from logging import getLogger
from multiprocessing import JoinableQueue as MpQueue
from typing import NamedTuple

from udemy_autocoupons.courses_store import CoursesStore
from udemy_autocoupons.enroller.state import DoneOrErrorT, State
from udemy_autocoupons.enroller.udemy_driver import UdemyDriver
from udemy_autocoupons.udemy_course import CourseWithCoupon

_printer = getLogger('printer')
_debug = getLogger('debug')


class RunResult(NamedTuple):
    """The result of the enroll_from_queue run."""
    coupons_not_working: set[CourseWithCoupon]
    blacklisted_courses: CoursesStore
    errors: set[CourseWithCoupon]


class Enroller:
    """A class that handles enrolling from a queue using a WebDriver."""

    _MAX_ATTEMPTS = 2

    def __init__(
        self,
        driver: UdemyDriver,
        mp_queue: MpQueue,
    ) -> None:
        """Stores the given driver and mp_queue.

        Args:
            driver: The WebDriver to use.
            mp_queue: The multiprocessing queue to get the courses from.

        """
        self._driver = driver
        self._mp_queue = mp_queue

        self._coupons_not_working: set[CourseWithCoupon] = set()
        self._blacklisted_courses = CoursesStore()
        self._errors: set[CourseWithCoupon] = set()

        self._enrolled_counter = 0

        self._attempts: defaultdict[CourseWithCoupon, int] = defaultdict(int)

    def enroll_from_queue(self) -> RunResult:
        """Enrolls in all courses in a queue, retrying if needed.

        When a None is received from the queue, it is considered that there won't be
        any more courses.

        Returns:
            The courses whose coupon doesn't work, the courses to blacklist for
            the next run for whatever reason and the courses that triggered an
            error.

        """
        while course := self._mp_queue.get():
            if course in self._blacklisted_courses:
                _debug.debug(
                    '%s is blacklisted. qsize is %s',
                    course,
                    self._mp_queue.qsize(),
                )
            else:
                state = self._driver.enroll(course)

                self._handle_state(course, state)

                qsize = self._mp_queue.qsize()
                _printer.info('%s courses left.', qsize)
                _debug.debug(
                    'Enroll finished for %s. qsize is %s',
                    course,
                    qsize,
                )

            self._mp_queue.task_done()
        _debug.debug('Got None in multiprocessing queue')

        self._mp_queue.task_done()

        run_result = RunResult(
            self._coupons_not_working,
            self._blacklisted_courses,
            self._errors,
        )
        _debug.debug('Run result was %s', run_result)

        _debug.debug('Enrolled in %s courses', self._enrolled_counter)
        _printer.info('Enrolled in %s courses', self._enrolled_counter)

        return run_result

    def _handle_state(
        self,
        course: CourseWithCoupon,
        state: DoneOrErrorT,
    ) -> None:
        if state is State.ENROLLED:
            self._enrolled_counter += 1

        if state in {
                State.ENROLLED,
                State.FREE,
                State.IN_ACCOUNT,
                State.UNAVAILABLE,
        }:
            self._blacklisted_courses.add(course.with_any_coupon())
        elif state is State.PAID:
            self._coupons_not_working.add(course)
        # Only case left is ERROR
        elif self._attempts[course] < self._MAX_ATTEMPTS:
            self._attempts[course] += 1
            self._mp_queue.put(course)
        else:
            self._errors.add(course)
