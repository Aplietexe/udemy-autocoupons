"""This module contains the UdemyCourse class."""
from dataclasses import dataclass
from logging import getLogger
from typing import Self
from urllib.parse import parse_qs, urlparse

_debug = getLogger('debug')


@dataclass(frozen=True)
class UdemyCourse:
    """Represents a Udemy Course.

    This class should not be instantiated directly. Instead use the from_url
    class method.

    Attributes:
        url_id: The id present in the URL path of the course (after /course/).
        coupon: The discount coupon.

    """
    url_id: str
    coupon: str | None

    @classmethod
    def from_url(cls: type[Self], url: str) -> Self | None:
        """Create a new Udemy Course from its URL.

        Args:
            url: The course URL.

        Returns:
            The new Udemy Course if the URL is valid, None otherwise.

        """
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query, strict_parsing=True)

        if not cls._verify(parsed.netloc, parsed.path):
            _debug.debug('%s cannot be parsed as a Udemy course', url)
            return None

        # 0 is '', 1 is 'course', 2 is the url_id
        url_id = parsed.path.split('/')[2]

        coupon = None

        if coupon_query_param := query_params.get('couponCode'):
            coupon = coupon_query_param[0]

        return cls(url_id, coupon)

    @staticmethod
    def _verify(netloc: str, path: str) -> bool:
        """Verifies that netloc and path match a valid Udemy Course URL.

        Args:
            netloc: netloc as returned by urllib.parse.urlparse.
            path: path as returned by urllib.parse.urlparse.

        Returns:
            True if the arguments correspond to a valid Udemy Course URL, false
            otherwise.

        """
        is_udemy = netloc in {'udemy.com', 'www.udemy.com'}

        # Avoid using regex
        has_course_url_id = (
            path.startswith('/course/') and
            len(path) > 8  # len('/course/') == 8
        )

        return is_udemy and has_course_url_id
