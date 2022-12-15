"""This module contains the UdemyDriver class."""
from __future__ import annotations

from collections.abc import Callable
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

_printer = getLogger('printer')
_debug = getLogger('debug')


class UdemyDriver:
    """Handles Udemy usage.

    Requires the profile set in PROFILE_DIRECTORY in USER_DATA_DIR to already be
    logged into the Udemy Account.

    Attributes:
        driver: The instance of UndetectedChromeDriver in use.

    """

    _ENROLL_BUTTON_SELECTOR = '[data-purpose*="buy-this-course-button"]'

    def __init__(self) -> None:
        """Starts the driver."""
        options = ChromeOptions()
        options.add_argument('--start-maximized')

        options.add_argument(f'--profile-directory={PROFILE_DIRECTORY}')
        options.add_argument(f'user-data-dir={USER_DATA_DIR}')

        _debug.debug(
            'Starting WebDriver with --profile-directory %s and user-data-dir %s',
            PROFILE_DIRECTORY,
            USER_DATA_DIR,
        )

        self.driver = Chrome(options=options)

        _debug.debug('Started WebDriver')

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
                'A WebDriverException was encountered while enrolling in %s',
                course,
            )
            _printer.error('Enroller: An error occurred while enrolling.')
            return State.ERROR

    def _enroll(self, course: CourseWithCoupon) -> DoneT:
        _debug.debug('Enrolling in %s', course.url)

        self.driver.get(course.url)

        if not self._course_is_available():
            _debug.debug('_course_is_available is False for %s', course.url)
            return State.UNAVAILABLE

        # The previous check guarantees that the button will show
        enroll_button = self._wait_for_clickable(self._ENROLL_BUTTON_SELECTOR)

        if (state := self._get_course_state()) != State.ENROLLABLE:
            return state

        enroll_button.click()

        if (state := self._checkout_is_correct()) != State.ENROLLABLE:
            # This is only intended as a safeguard, the execution should never
            # hit this branch
            _debug.error(
                '_checkout_is_correct returned %s for %s',
                state,
                course.url,
            )
            return state

        checkout_button = self._wait_for_clickable(
            '[class*="checkout-button--checkout-button--button"]',
        )
        checkout_button.click()

        self._wait.until(lambda driver: 'checkout' not in driver.current_url)
        return State.ENROLLED

    def _course_is_available(self) -> bool:
        """Check if the current course on screen is available.

        The detection looks for either a redirect to a blacklisted route, to /,
        a banner indicating that the course is unavailable, a 404 error banner,
        a private course button or the enroll button. Only in the last case the
        course is available.

        Returns:
           True if the current course is available, False otherwise.

        """
        blacklist = ('/topic/', '/it-and-software/it-certification/')
        unavailable_selector = '[class*="limited-access-container--content"]'
        banner404_selector = '.error__container'
        private_button_selector = '[class*="course-landing-page-private"]'

        self._wait.until(
            EC.any_of(
                *(EC.url_contains(blacklisted) for blacklisted in blacklist),
                EC.url_to_be('https://www.udemy.com/'),
                self._ec_located(unavailable_selector),
                self._ec_located(banner404_selector),
                self._ec_located(self._ENROLL_BUTTON_SELECTOR),
                self._ec_located(private_button_selector),
            ),
        )

        unavailable_elements = self._find_elements(unavailable_selector)
        banner404_elements = self._find_elements(banner404_selector)
        private_button_elements = self._find_elements(private_button_selector)

        _debug.debug(
            'Url: %s; unavailable: %s; banner404: %s; private_button: %s',
            self.driver.current_url,
            unavailable_elements,
            banner404_elements,
            private_button_elements,
        )

        return (
            all(
                blacklisted not in self.driver.current_url
                for blacklisted in blacklist
            ) and self.driver.current_url != 'https://www.udemy.com/' and
            not unavailable_elements and not banner404_elements and
            not private_button_elements
        )

    def _get_course_state(
        self,
    ) -> Literal[State.IN_ACCOUNT, State.FREE, State.PAID, State.ENROLLABLE]:
        """Checks the state of the course in screen.

        Returns:
            The state of the course.

        """
        purchased_selector = '[class*="purchase-info"]'
        price_selector = '[data-purpose*="course-price-text"] span:not(.ud-sr-only)'
        free_badge_selector = '.ud-badge-free'

        self._wait.until(
            EC.any_of(
                self._ec_located(purchased_selector),
                self._ec_located(price_selector),
                self._ec_located(free_badge_selector),
            ),
        )

        if self._find_elements(purchased_selector):
            _debug.debug(
                'Found purchased_selector in %s',
                self.driver.current_url,
            )

            return State.IN_ACCOUNT

        if self._find_elements(free_badge_selector):
            _debug.debug(
                'Found free_badge_selector in %s',
                self.driver.current_url,
            )

            return State.FREE

        # Wait first so that we can then use find_element instead of nesting waits
        self._wait_for(price_selector)

        # Sometimes the element renders before its text
        price_text: str = self._wait.until(
            lambda driver: driver.find_element(By.CSS_SELECTOR, price_selector).
            text,
        )

        _debug.debug('price_text is %s', price_text)

        return State.PAID if '$' in price_text else State.ENROLLABLE

    def _checkout_is_correct(
        self,
    ) -> Literal[State.IN_ACCOUNT, State.FREE, State.ENROLLABLE]:
        """Checks that the state of the course in the checkout is correct.

        This is a fallback in case _get_course_state fails.

        Returns:
            The state of the course.

        """
        total_amount_locator = '[data-purpose*="total-amount-summary"] span:nth-child(2)'

        self._wait.until(
            EC.any_of(
                EC.url_contains('/learn/lecture/'),
                EC.url_contains('/cart/subscribe/course/'),
                self._ec_located(total_amount_locator),
            ),
        )

        _debug.debug('Url is %s', self.driver.current_url)

        if '/learn/lecture/' in self.driver.current_url:
            return State.IN_ACCOUNT

        if '/cart/subscribe/course/' in self.driver.current_url:
            return State.FREE

        total_amount_text = self._wait_for(total_amount_locator).text

        _debug.debug('Total amount text is %s', total_amount_text)

        return State.ENROLLABLE if (
            total_amount_text.startswith('0')
        ) else State.FREE

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
        return self._wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector)),
        )

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
    def _ec_located(css_selector: str) -> Callable[[Chrome], WebElement]:
        """Creates an expected condition for locating the given selector.

        Args:
            css_selector: The CSS selector of the element.

        Returns:
            An expected condition which returns the found element.

        """
        return EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
