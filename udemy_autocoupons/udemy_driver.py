"""This module contains the UdemyDriver class."""
from __future__ import annotations

from collections.abc import Callable
from logging import getLogger
from multiprocessing import JoinableQueue as MpQueue

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
from udemy_autocoupons.udemy_course import UdemyCourse

_printer = getLogger('printer')
_debug = getLogger('debug')


class UdemyDriver:
    """Handles Udemy usage.

    Requires the profile set in PROFILE_DIRECTORY in USER_DATA_DIR to already be
    logged into the Udemy Account.

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

    def enroll_from_queue(self, mp_queue: MpQueue[UdemyCourse | None]) -> None:  # pylint: disable=unsubscriptable-object
        """Enrolls in all courses in a queue.

        When a None is received from the queue, it is considered that there
        won't be any more courses.

        Args:
            mp_queue: A multiprocessing queue with courses.

        """
        while course := mp_queue.get():
            self.enroll(course)

            qsize = mp_queue.qsize()
            _printer.info('%s courses left.', qsize)
            _debug.debug('Enroll finished for %s. qsize is %s', course, qsize)

            mp_queue.task_done()

        _debug.debug('Got None in multiprocessing queue')

        mp_queue.task_done()

    def enroll(self, course: UdemyCourse) -> None:
        """If the course is discounted, it enrolls the account in it.

        Args:
            course: The course to enroll in.

        """
        try:
            self._enroll(course)
        except WebDriverException:
            _debug.exception(
                'A WebDriverException was encountered while enrolling in %s',
                course,
            )
            _printer.error('An error occurred while enrolling, skipping course')

    def _enroll(self, course: UdemyCourse) -> None:
        _debug.debug('Enrolling in %s', course.url)

        self.driver.get(course.url)

        if not self._course_is_available():
            _debug.debug('_course_is_available failed for %s', course.url)
            return

        # The previous check guarantees that the button will show
        enroll_button = self._wait_for_clickable(self._ENROLL_BUTTON_SELECTOR)

        if not self._current_course_is_discounted():
            _debug.debug('_course_is_discounted failed for %s', course.url)
            return

        enroll_button.click()

        if not self._checkout_is_correct():
            _debug.error('_checkout_is_correct failed for %s', course.url)
            return

        checkout_button = self._wait_for_clickable(
            '[class*="checkout-button--checkout-button--button"]',
        )
        checkout_button.click()

        self._wait.until(lambda driver: 'checkout' not in driver.current_url)

    def quit(self) -> None:
        """Quits the WebDriver instance."""
        self.driver.quit()

    def _course_is_available(self) -> bool:
        """Check if the current course on screen is available.

        The detection looks for either a redirect to a blacklisted route, to /,
        a banner indicating that the course is unavailable a 404 error banner, a
        private course button or the enroll button. Only in the last case the
        course is available.

        Args:
          enroll_button_selector: The CSS selector of the enroll button, which
          shows only if the course is available.

        Returns:
           True if the current course is available, False otherwise

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

        return (
            all(
                blacklisted not in self.driver.current_url
                for blacklisted in blacklist
            ) and self.driver.current_url != 'https://www.udemy.com/' and
            not self._find_elements(unavailable_selector) and
            not self._find_elements(banner404_selector) and
            not self._find_elements(private_button_selector)
        )

    def _current_course_is_discounted(self) -> bool:
        """Check if the course currently on screen is discounted.

        A course is considered discounted if it's not always free, it's not
        already purchased and currently it's free temporarily.

        Returns:
            True if the course is discounted, False otherwise

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

        return (
            not self._find_elements(purchased_selector) and
            not self._find_elements(free_badge_selector) and
            '$' not in self._wait_for(price_selector).text
        )

    def _checkout_is_correct(self) -> bool:
        """Checks that the screen is a checkout and the course is free.

        This is a fallback in case _current_course_is_discounted returns a false
        positive.

        Returns:
            True if the checkout is correct, False otherwise.

        """
        total_amount_locator = '[data-purpose*="total-amount-summary"] span:nth-child(2)'

        self._wait.until(
            EC.any_of(
                EC.url_contains('/learn/lecture/'),
                EC.url_contains('/cart/subscribe/course/'),
                self._ec_located(total_amount_locator),
            ),
        )

        if '/cart/checkout/express/course/' not in self.driver.current_url:
            return False

        return self._wait_for(total_amount_locator).text.startswith('0')

    def _wait_for(self, css_selector: str) -> WebElement:
        return self._wait.until(self._ec_located(css_selector))

    def _wait_for_clickable(self, css_selector: str) -> WebElement:
        return self._wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector)),
        )

    def _find(self, css_selector: str) -> WebElement:
        return self.driver.find_element(By.CSS_SELECTOR, css_selector)

    def _find_elements(self, css_selector: str) -> list[WebElement]:
        return self.driver.find_elements(By.CSS_SELECTOR, css_selector)

    @staticmethod
    def _ec_located(css_selector: str) -> Callable[[Chrome], WebElement]:
        return EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
