"""This module contains the FreshcouponsScraper scraper."""

from asyncio import Queue as AsyncQueue
from dataclasses import dataclass
from logging import getLogger
from threading import Event
from typing import TypedDict

from aiohttp import ClientSession

from udemy_autocoupons.request_with_reattempts import request_with_reattempts
from udemy_autocoupons.scrapers.scraper import Scraper

_printer = getLogger("printer")
_debug = getLogger("debug")

# disable Flake8 N815


class _JsonMeta(TypedDict):
    """The type of the meta.json file."""

    lastSynced: str  # noqa: N815


class _CourseDetails(TypedDict):
    courseUri: str  # noqa: N815


class _CouponData(TypedDict):
    couponCode: str  # noqa: N815
    discountedPrice: str  # noqa: N815


class _CourseEntry(TypedDict):
    courseDetails: _CourseDetails  # noqa: N815
    isAlreadyAFreeCourse: bool  # noqa: N815
    couponData: _CouponData  # noqa: N815


class _JsonCourses(TypedDict):
    """The type of the courses json file."""

    coursesWithCoupon: dict[str, _CourseEntry]  # noqa: N815


@dataclass(frozen=True, slots=True)
class _FormattedCourse:
    """The type of the course entry after formatting."""

    url: str
    discounted_price: str
    is_already_free: bool


class FreshcouponsScraper(Scraper):
    """Handles scraping of coupons from the Chrome extension Freshcoupons."""

    _BASE = "https://raw.githubusercontent.com/fresh-coupons/fresh-coupons-data/main/udemy/v2"

    def __init__(
        self,
        queue: AsyncQueue[str | None],
        client: ClientSession,
        persistent_data: None,
        stop_event: Event,
    ) -> None:
        """Stores provided parameters.

        Args:
          queue: An async queue where the urls will be added.
          client: An aiohttp client to use.
          persistent_data: The persistent data previously returned.
          stop_event: An event that will be set on an early stop.
        """
        self._queue = queue
        self._client = client
        self._stop_event = stop_event

    async def scrap(self) -> None:
        """Scrapes the Freshcoupons website for free courses and adds them to the queue."""
        _debug.debug("Start scraping")

        if not (timestamp := await self._request_timestamp()):
            return

        if not (courses_json := await self._request_courses(timestamp)):
            return

        if not (formatted_courses := self._format_courses(courses_json)):
            return

        for course in formatted_courses:
            if course.discounted_price == "Free" and not course.is_already_free:
                await self._queue.put(course.url)

    def create_persistent_data(self) -> None:
        """Creates the persistent data for this scraper."""

    async def _request_timestamp(self) -> str | None:
        """Gets the timestamp from the meta.json file.

        Returns:
          The timestamp or None if an error occurred.
        """
        meta: _JsonMeta | None = await request_with_reattempts(
            f"{self._BASE}/meta.json",
            "json",
            self._client,
            self._stop_event,
        )

        if not meta:
            _debug.error("Failed to get meta.json")
            _printer.error("Failed to get Freshcoupons metadata")
            return None

        timestamp = None
        try:
            timestamp = meta["lastSynced"]
        except (KeyError, TypeError):
            _debug.exception("Failed to get lastSynced from meta.json")
            _printer.error("Failed to get Freshcoupons metadata")

        return timestamp

    async def _request_courses(self, last_synced: str) -> _JsonCourses | None:
        """Gets the courses json file.

        Args:
          last_synced: The timestamp to use in the URL.

        Returns:
          The courses json file or None if an error occurred.
        """
        json_courses_res: _JsonCourses | None = await request_with_reattempts(
            f"{self._BASE}/{last_synced}.json",
            "json",
            self._client,
            self._stop_event,
        )

        if not json_courses_res:
            _debug.error("Failed to get courses json file")
            _printer.error("Failed to get Freshcoupons courses")
            return None

        _debug.debug(
            "Got %s courses",
            len(json_courses_res["coursesWithCoupon"]),
        )

        return json_courses_res

    @classmethod
    def _format_courses(
        cls,
        courses: _JsonCourses,
    ) -> list[_FormattedCourse] | None:
        """Formats the courses to the desired format, handling exceptions.

        Args:
          courses: The courses to format.

        Returns:
          The formatted courses or None if an exception occurred.
        """
        try:
            return cls._try_to_format_courses(courses)
        except (KeyError, TypeError):
            _debug.exception(
                "Failed to format courses. Response was %s",
                courses,
            )
            _printer.error("ERROR formatting Freshcoupons courses. Check logs.")
            return None

    @staticmethod
    def _try_to_format_courses(courses: _JsonCourses) -> list[_FormattedCourse]:
        """Formats the courses to the desired format.

        Args:
          courses: The courses to format.

        Returns:
          The formatted courses.
        """
        formatted_courses: list[_FormattedCourse] = []

        for course in courses["coursesWithCoupon"].values():
            url = course["courseDetails"]["courseUri"]
            url += f"/?couponCode={course['couponData']['couponCode']}"
            formatted_courses.append(
                _FormattedCourse(
                    url,
                    course["couponData"]["discountedPrice"],
                    course["isAlreadyAFreeCourse"],
                ),
            )

        return formatted_courses
