"""This module contains the CoursesStore class."""
from collections.abc import Iterator, MutableSet
from dataclasses import astuple

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
        self._any_coupon: dict[str, CourseWithAnyCoupon] = {}

        for course in args:
            self.add(course)

    def __contains__(self, course: UdemyCourseT) -> bool:
        """Checks if the given element is in the store."""
        if course.url_id in self._any_coupon:
            return True

        return False if course.any_coupon else course in self._specific_coupon

    def __iter__(self) -> Iterator[UdemyCourseT]:
        """Iterates first over the courses with a specific coupon."""
        yield from self._specific_coupon
        yield from self._any_coupon.values()

    def __len__(self) -> int:
        """Returns the number of items in the store.

        This number could be reduced after calling optimize().

        """
        return len(self._any_coupon) + len(self._specific_coupon)

    def __repr__(self) -> str:
        """String representation of the object.

        Is such that eval(repr(courses_store))==courses_store.

        """
        repr_ = 'CoursesStore('

        if self._specific_coupon:
            specific_repr = repr(self._specific_coupon)[1:-1]
            repr_ += f'{specific_repr}, '

        if self._any_coupon:
            any_coupon_set = set(self._any_coupon.values())
            repr_ += repr(any_coupon_set)[1:-1]

        repr_ += ')'

        return repr_

    def add(self, course: UdemyCourseT) -> None:
        """Adds a course to the store."""
        if is_with_any_coupon(course):
            self._any_coupon[course.url_id] = course
        elif is_with_specific_coupon(course):
            self._specific_coupon.add(course)
        else:
            raise TypeError

    def discard(self, course: UdemyCourseT) -> None:
        """Removes a course without raising if it doesn't exist."""
        if is_with_any_coupon(course) and course.url_id in self._any_coupon:
            self._any_coupon.pop(course.url_id)
        elif is_with_specific_coupon(course):
            self._specific_coupon.discard(course)
        else:
            raise TypeError

    def optimize(self) -> None:
        """Optimizes the memory usage by removing redundant courses."""
        for specific_coupon in self._specific_coupon:
            if specific_coupon.url_id in self._any_coupon:
                self._specific_coupon.remove(specific_coupon)

    def create_compressed(self) -> tuple[str | tuple[str, str], ...]:
        """Creates a smaller representation of the store.

        The store can be recreated by using load_compressed with the return
        value of this method.

        Returns:
            The compressed representation.

        """
        self.optimize()
        return tuple(self._any_coupon.keys()) + tuple(
            astuple(specific_coupon)
            for specific_coupon in self._specific_coupon
        )

    def load_compressed(
        self,
        compressed: tuple[str | tuple[str, str], ...],
    ) -> None:
        """Loads courses into the store from a compressed representation.

        Args:
            compressed: The compressed representation, as returned by
            create_compressed.

        """
        for compressed_course in compressed:
            if isinstance(compressed_course, str):
                self.add(CourseWithAnyCoupon(compressed_course))
            else:
                self.add(CourseWithCoupon(*compressed_course))
