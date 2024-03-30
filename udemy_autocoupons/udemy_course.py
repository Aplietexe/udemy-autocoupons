"""This module contains the UdemyCourse class."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from logging import getLogger
from typing import Literal, TypeGuard, overload

from yarl import URL

_debug = getLogger("debug")


@dataclass(frozen=True, slots=True)
class _UdemyCourse(ABC):
    """Represents a Udemy Course.

    This class should not be instantiated directly, but it has no abstract
    methods, so no error will be raised.

    Attributes:
        url_id: The id present in the URL path of the course (after /course/).
        coupon: The discount coupon.

    """

    url_id: str
    coupon: str | None
    any_coupon: bool

    @property
    def url(self) -> str:
        """Creates the URL for the course with the coupon if it exists.

        Returns:
            The URL.

        """
        url = f"https://www.udemy.com/course/{self.url_id}/"

        if self.coupon:
            url += f"?couponCode={self.coupon}"

        return url

    @overload
    @staticmethod
    def from_url(
        url_str: str,
        any_coupon: Literal[False] = False,
    ) -> CourseWithCoupon | None: ...

    @overload
    @staticmethod
    def from_url(
        url_str: str,
        any_coupon: Literal[True],
    ) -> CourseWithAnyCoupon | None: ...

    @staticmethod
    def from_url(url_str: str, any_coupon: bool = False) -> UdemyCourseT | None:
        """Create a new UdemyCourse from its URL.

        Args:
            url_str: The course URL.
            any_coupon: Whether the course should be UdemyCourseWithAnyCoupon or
            UdemyCourseWithSpecificCoupon

        Returns:
            The new Udemy Course if the URL is valid, None otherwise.

        """
        url_str = url_str.encode("ascii", "ignore").decode("ascii")
        url = URL(url_str)

        if url.host not in {"udemy.com", "www.udemy.com"} or len(url.path) < 2:
            _debug.debug("%s cannot be parsed as a Udemy course", url_str)
            return None

        url_parts = url.path.split("/")
        if url_parts[1] != "course" and len(url_parts) <= 2:
            _debug.debug("%s cannot be parsed as a Udemy course", url_str)
            return None

        url_id = url_parts[2] if url_parts[1] == "course" else url_parts[1]

        if any_coupon:
            return CourseWithAnyCoupon(url_id)

        coupon = url.query.get("couponCode")
        return CourseWithCoupon(url_id, coupon)


@dataclass(frozen=True, slots=True)
class CourseWithAnyCoupon(_UdemyCourse):
    """A subclass of UdemyCourse with any_coupon==True.

    In this subclass, coupon is always None.

    """

    coupon: None = field(default=None, repr=False)
    any_coupon: Literal[True] = field(default=True, repr=False)


@dataclass(frozen=True, slots=True)
class CourseWithCoupon(_UdemyCourse):
    """A subclass of UdemyCourse with any_coupon==False.

    Note that coupon could still be None, which means specifically the course
    without any coupon.

    """

    coupon: str | None
    any_coupon: Literal[False] = field(default=False, repr=False)

    def with_any_coupon(self) -> CourseWithAnyCoupon:
        """Returns a UdemyCourseWithAnyCoupon with the same url_id.

        Returns:
            The new course.

        """
        return CourseWithAnyCoupon(self.url_id)


UdemyCourseT = CourseWithAnyCoupon | CourseWithCoupon


def is_with_any_coupon(course: UdemyCourseT) -> TypeGuard[CourseWithAnyCoupon]:
    """Check if a UdemyCourse is a UdemyCourseWithAnyCoupon."""
    return course.any_coupon


def is_with_specific_coupon(
    course: UdemyCourseT,
) -> TypeGuard[CourseWithCoupon]:
    """Check if a UdemyCourse is a UdemyCourseWithSpecificCoupon."""
    return not course.any_coupon
