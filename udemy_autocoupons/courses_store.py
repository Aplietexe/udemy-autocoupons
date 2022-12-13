"""This module contains the CoursesStore class."""
from collections.abc import Iterator, MutableSet

from udemy_autocoupons.udemy_course import (
    CourseWithAnyCoupon,
    CourseWithCoupon,
    UdemyCourseT,
    is_with_any_coupon,
    is_with_specific_coupon,
)


class CoursesStore(MutableSet):
    """A set-like store for mixed UdemyCourse instances.

    This store considers that if it contains a course with any_coupon, then all
    courses that have the same url_id are contained too.

    """

    def __init__(self, *args: UdemyCourseT) -> None:
        """Adds all passed courses to the store."""
        self._specific_coupon: set[CourseWithCoupon] = set()
        self._any_coupon: set[CourseWithAnyCoupon] = set()

        for course in args:
            self.add(course)

    def __contains__(self, course: UdemyCourseT) -> bool:
        """Checks if the given element is in the store."""
        if course.any_coupon:
            return course in self._any_coupon

        if course in self._specific_coupon:
            return True

        return any(
            stored_course.url_id == course.url_id
            for stored_course in self._any_coupon
        )

    def __iter__(self) -> Iterator[UdemyCourseT]:
        """Iterates first over the courses with any_coupon==True."""
        yield from self._any_coupon
        yield from self._specific_coupon

    def __len__(self) -> int:
        """Returns the number of items in the store.

        This number could be reduced after calling optimize().

        """
        return len(self._any_coupon) + len(self._specific_coupon)

    def add(self, course: UdemyCourseT) -> None:
        """Adds a course to the store."""
        if is_with_any_coupon(course):
            self._any_coupon.add(course)
        elif is_with_specific_coupon(course):
            self._specific_coupon.add(course)
        else:
            raise TypeError

    def discard(self, course: UdemyCourseT) -> None:
        """Removes a course without raising if it doesn't exist."""
        if is_with_any_coupon(course):
            self._any_coupon.discard(course)
        elif is_with_specific_coupon(course):
            self._specific_coupon.discard(course)
        else:
            raise TypeError

    def optimize(self) -> None:
        """Optimizes the memory usage by removing redundant courses."""
        for any_coupon in self._any_coupon:
            for specific_coupon in self._specific_coupon:
                if specific_coupon.url_id == any_coupon.url:
                    self._specific_coupon.remove(specific_coupon)
