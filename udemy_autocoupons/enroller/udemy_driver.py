"""This module contains the UdemyDriver class."""
from __future__ import annotations

from collections.abc import Callable
from functools import partial
from logging import getLogger
from typing import Literal

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.wait import WebDriverWait
from undetected_chromedriver import Chrome, ChromeOptions

from udemy_autocoupons.constants import (
    PROFILE_DIRECTORY,
    USER_DATA_DIR,
    WAIT_POLL_FREQUENCY,
    WAIT_TIMEOUT,
)
from udemy_autocoupons.enroller.state import DoneOrErrorT, DoneT, State
from udemy_autocoupons.udemy_course import CourseWithCoupon

_printer = getLogger("printer")
_debug = getLogger("debug")

_CheckedStateT = Literal[State.PAID, State.TO_BLACKLIST, State.ENROLLABLE]

_ExpectedConditionT = Callable[[Chrome], WebElement | Literal[False]]


class UdemyDriver:
    """Handles Udemy usage.

    Requires the profile set in PROFILE_DIRECTORY in USER_DATA_DIR to already be
    logged into the Udemy Account.

    Attributes:
        driver: The instance of UndetectedChromeDriver in use.

    """

    _SELECTORS = {
        "ENROLL_BUTTON": '[data-purpose*="buy-this-course-button"]',
        "FREE_BADGE": ".ud-badge-free",
        "PURCHASED": '[class*="purchase-info"]',
        "FREE_COURSE": '[class*="generic-purchase-section--free-course"]',
    }

    def __init__(self) -> None:
        """Starts the driver."""
        options = ChromeOptions()
        options.add_argument("--start-maximized")

        options.add_argument(f"--profile-directory={PROFILE_DIRECTORY}")
        options.add_argument(f"user-data-dir={USER_DATA_DIR}")

        _debug.debug(
            "Starting WebDriver with --profile-directory %s and user-data-dir %s",
            PROFILE_DIRECTORY,
            USER_DATA_DIR,
        )

        self.driver = Chrome(options=options)

        _debug.debug("Started WebDriver")

        self._wait = WebDriverWait(
            self.driver,
            WAIT_TIMEOUT,
            WAIT_POLL_FREQUENCY,
        )

    def quit(self) -> None:
        """Quits the WebDriver instance."""
        self.driver.quit()

    def enroll(self, course: CourseWithCoupon) -> DoneOrErrorT:
        """If the course is discounted, it enrolls the account in it.

        Args:
            course: The course to enroll in.

        Returns:
            The state of the course after trying to enroll.

        """
        try:
            return self._enroll(course)
        except WebDriverException:
            _debug.exception(
                "A WebDriverException was encountered while enrolling in %s",
                course,
            )
            _printer.error("Enroller: An error occurred while enrolling.")
            return State.ERROR

    def _enroll(self, course: CourseWithCoupon) -> DoneT:
        _debug.debug("Enrolling in %s", course.url)

        self.driver.get(course.url)

        if (state := self._fast_course_state(course)) != State.ENROLLABLE:
            _debug.debug("_fast_course_state is %s for %s", state, course.url)
            return state

        if (state := self._get_course_state()) != State.ENROLLABLE:
            _debug.debug("_get_course_state is %s for %s", state, course.url)
            return state

        self._wait_for_clickable(self._SELECTORS["ENROLL_BUTTON"]).click()

        if (state := self._checkout_is_correct()) != State.ENROLLABLE:
            # This is only intended as a safeguard, the execution should never
            # hit this branch
            _debug.error(
                "_checkout_is_correct returned %s for %s",
                state,
                course.url,
            )
            return state

        checkout_button_selector = (
            '[class*="checkout-button--checkout-button--button"]'
        )

        self._wait.until(
            EC.all_of(
                self._ec_clickable(checkout_button_selector),
                self._ec_cursor_allowed(checkout_button_selector),
            ),
        )

        self._find(checkout_button_selector).click()

        self._wait.until(lambda driver: "checkout" not in driver.current_url)
        return State.ENROLLED

    def _fast_course_state(self, course: CourseWithCoupon) -> _CheckedStateT:
        """Check if the current course on screen is enrollable.

        This might return a false positive, but it's the fastest method so it
        should be used first.

        Returns:
           True if the current course is enrollable, False otherwise.

        """
        unavailable_selector = '[class*="limited-access-container--content"]'
        banner404_selector = ".error__container"
        private_button_selector = '[class*="course-landing-page-private"]'

        checks = [
            EC.url_contains("/topic/"),
            EC.url_contains("/courses/"),
            EC.url_contains("/draft/"),
            EC.url_to_be("https://www.udemy.com/"),
            self._ec_located(unavailable_selector),
            self._ec_located(banner404_selector),
            self._ec_located(private_button_selector),
            self._ec_located(self._SELECTORS["ENROLL_BUTTON"]),
            self._ec_located(self._SELECTORS["FREE_BADGE"]),
            self._ec_located(self._SELECTORS["PURCHASED"]),
        ]

        if course.coupon:
            checks.append(EC.url_to_be(course.with_any_coupon().url))

        self._wait.until(EC.any_of(*checks))

        unavailable_elements = self._find_elements(unavailable_selector)
        banner404_elements = self._find_elements(banner404_selector)
        private_button_elements = self._find_elements(private_button_selector)
        free_badge_elements = self._find_elements(self._SELECTORS["PURCHASED"])
        purchased_elements = self._find_elements(self._SELECTORS["FREE_BADGE"])
        free_course_elements = self._find_elements(
            self._SELECTORS["FREE_COURSE"],
        )

        _debug.debug(
            "Url: %s; unavailable: %s; banner404: %s",
            self.driver.current_url,
            unavailable_elements,
            banner404_elements,
        )
        _debug.debug(
            "private_button: %s; free_badge: %s; purchased: %s; free_course: %s",
            private_button_elements,
            free_badge_elements,
            purchased_elements,
            free_course_elements,
        )

        to_blacklist = (
            "/topic/" in self.driver.current_url
            or "/courses/" in self.driver.current_url
            or "/draft/" in self.driver.current_url
            or self.driver.current_url == "https://www.udemy.com/"
            or unavailable_elements
            or banner404_elements
            or private_button_elements
            or free_badge_elements
            or purchased_elements
            or free_course_elements
        )

        if to_blacklist:
            return State.TO_BLACKLIST

        if self.driver.current_url == course.with_any_coupon().url:
            return State.PAID

        return State.ENROLLABLE

    def _get_course_state(self) -> _CheckedStateT:
        """Checks the state of the course in screen.

        Returns:
            The state of the course.

        """
        price_selector = (
            '[data-purpose*="course-price-text"] span:not(.ud-sr-only)'
        )

        self._wait.until(
            EC.any_of(
                self._ec_located(self._SELECTORS["PURCHASED"]),
                self._ec_located(price_selector),
                self._ec_located(self._SELECTORS["FREE_BADGE"]),
                self._ec_located(self._SELECTORS["FREE_COURSE"]),
            ),
        )

        free_badge_elements = self._find_elements(self._SELECTORS["FREE_BADGE"])
        purchased_elements = self._find_elements(self._SELECTORS["PURCHASED"])
        free_course_elements = self._find_elements(
            self._SELECTORS["FREE_COURSE"],
        )

        if free_badge_elements or purchased_elements or free_course_elements:
            _debug.debug(
                "In %s, free badge %s, purchased, %s, free course %s",
                self.driver.current_url,
                free_badge_elements,
                purchased_elements,
                free_course_elements,
            )

            return State.TO_BLACKLIST

        # Wait first so that we can then use find_element instead of nesting waits
        self._wait_for(price_selector)

        # Sometimes the element renders before its text
        price_text: str = self._wait.until(
            lambda driver: driver.find_element(
                By.CSS_SELECTOR,
                price_selector,
            ).text,
        )

        _debug.debug("price_text is %s", price_text)

        return State.PAID if "$" in price_text else State.ENROLLABLE

    def _checkout_is_correct(self) -> _CheckedStateT:
        """Checks that the state of the course in the checkout is correct.

        This is a fallback in case _get_course_state fails.

        Returns:
            The state of the course.

        """
        total_amount_locator = (
            '[data-purpose*="total-amount-summary"] span:nth-child(2)'
        )

        self._wait.until(
            EC.any_of(
                EC.url_contains("/learn/lecture/"),
                EC.url_contains("/cart/subscribe/course/"),
                self._ec_located(total_amount_locator),
            ),
        )

        _debug.debug("Url is %s", self.driver.current_url)

        if (
            "/learn/lecture/" in self.driver.current_url
            or "/cart/subscribe/course/" in self.driver.current_url
        ):
            return State.TO_BLACKLIST

        total_amount_text = self._wait_for(total_amount_locator).text

        _debug.debug("Total amount text is %s", total_amount_text)

        return (
            State.ENROLLABLE
            if total_amount_text.startswith("0")
            else State.PAID
        )

    def _wait_for(self, css_selector: str) -> WebElement:
        """Waits until the element with the given CSS selector is located.

        Args:
            css_selector: The CSS selector of the element.

        Returns:
            The element once it's found.

        """
        return self._wait.until(self._ec_located(css_selector))

    def _wait_for_clickable(self, css_selector: str) -> WebElement:
        """Waits until the element with the given CSS selector is clickable.

        Args:
            css_selector: The CSS selector of the element.

        Returns:
            The element once it's clickable.

        """
        return self._wait.until(self._ec_clickable(css_selector))

    def _find(self, css_selector: str) -> WebElement:
        """Finds without waiting the element with the given CSS selector.

        Args:
            css_selector: The CSS selector of the element.

        Returns:
            The element.

        Raises:
            NoSuchElementException: If the element is not found.

        """
        return self.driver.find_element(By.CSS_SELECTOR, css_selector)

    def _find_elements(self, css_selector: str) -> list[WebElement]:
        """Finds without waiting the elements with the given CSS selector.

        Args:
            css_selector: The CSS selector of the element.

        Returns:
            A list of elements, which can be empty if no elements were found.

        """
        return self.driver.find_elements(By.CSS_SELECTOR, css_selector)

    @staticmethod
    def _ec_located(css_selector: str) -> _ExpectedConditionT:
        """Creates an expected condition for locating the given selector.

        Args:
            css_selector: The CSS selector of the element.

        Returns:
            An expected condition which returns the found element.

        """
        return EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))

    @staticmethod
    def _ec_clickable(css_selector: str) -> _ExpectedConditionT:
        """Creates an expected condition for the given selector to be clickable.

        Args:
            css_selector: The CSS selector of the element.

        Returns:
            An expected condition which returns the found element.

        """
        return EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))

    @staticmethod
    def _cursor_to_be_allowed(
        css_selector: str,
        driver: Chrome,
    ) -> WebElement | Literal[False]:
        """An expected condition for the cursor to be allowed.

        Args:
            css_selector: The CSS selector of the element.
            driver: The Chrome WebDriver to use.

        """
        target = driver.find_element(By.CSS_SELECTOR, css_selector)

        if target.value_of_css_property("cursor") != "not-allowed":
            return target

        return False

    @classmethod
    def _ec_cursor_allowed(cls, css_selector: str) -> _ExpectedConditionT:
        """Creates an expected condition for the cursor to be allowed.

        Args:
            css_selector: The CSS selector of the element.

        Returns:
            An expected condition which returns the found element.

        """
        return partial(cls._cursor_to_be_allowed, css_selector)
