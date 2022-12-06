"""This module contains the UdemyDriver class."""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.wait import WebDriverWait

from udemy_autocoupons.constants import (
    PROFILE_DIRECTORY,
    USER_DATA_DIR,
    WAIT_POLL_FREQUENCY,
    WAIT_TIMEOUT,
)
from udemy_autocoupons.udemy_course import UdemyCourse


class UdemyDriver:
    """Handles Udemy usage.

    Requires the profile set in PROFILE_DIRECTORY in USER_DATA_DIR to already be
    logged into the Udemy Account.

    """

    def __init__(self) -> None:
        """Starts the driver."""
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')

        options.add_argument(f'--profile-directory={PROFILE_DIRECTORY}')
        options.add_argument(f'user-data-dir={USER_DATA_DIR}')

        self.driver = uc.Chrome(options=options)

        self._wait = WebDriverWait(
            self.driver,
            WAIT_TIMEOUT,
            WAIT_POLL_FREQUENCY,
        )

    def _wait_for(self, locator: tuple[str, str]) -> WebElement:
        return self._wait.until(EC.presence_of_element_located(locator))

    def enroll(self, course: UdemyCourse) -> None:
        """If the course is discounted, it enrolls the account in it.

        Args:
            course: The course to enroll in.

        """
        url = f'https://www.udemy.com/course/{course.url_id}/?couponCode={course.coupon}'

        self.driver.get(url)

        # This shows even if the course is not discounted, so it's a safe wait
        enroll_button: WebElement = self._wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-purpose*="buy-this-course-button"]'),
            ),
        )

        if not self._current_course_is_discounted():
            return

        enroll_button.click()

        if not self._checkout_is_correct():
            return

        checkout_button = self._wait.until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                '[class*="checkout-button--checkout-button--button"]',
            )),
        )
        checkout_button.click()

        self._wait.until(lambda driver: 'checkout' not in driver.current_url)

    def _current_course_is_discounted(self) -> bool:
        """Check if the course currently on screen is discounted.

        A course is considered discounted if it's not always free, it's not
        already purchased and currently it's free temporarily.

        Returns:
            True if the course is discounted, False otherwise

        """
        purchased_locator = (
            By.CSS_SELECTOR,
            '[class*="purchase-info"]',
        )
        price_locator = (
            By.CSS_SELECTOR,
            '[data-purpose*="course-price-text"] span:not(.ud-sr-only)',
        )
        free_badge_locator = (By.CSS_SELECTOR, '.ud-badge-free')

        self._wait.until(
            EC.any_of(
                EC.presence_of_element_located(purchased_locator),
                EC.presence_of_element_located(price_locator),
                EC.presence_of_element_located(free_badge_locator),
            ),
        )

        return (
            not self.driver.find_elements(*purchased_locator) and
            not self.driver.find_elements(*free_badge_locator) and
            '$' not in self.driver.find_elements(*price_locator)[0].text
        )

    def _checkout_is_correct(self) -> bool:
        """Checks that the screen is a checkout and the course is free.

        This is a fallback in case _current_course_is_discounted returns a false
        positive.

        Returns:
            True if the checkout is correct, False otherwise.

        """
        self._wait.until(
            EC.any_of(
                EC.url_contains('/learn/lecture/'),
                EC.url_contains('/cart/subscribe/course/'),
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    '[data-purpose*="total-amount-summary"] span:nth-child(2)',
                )),
            ),
        )

        if '/cart/checkout/express/course/' not in self.driver.current_url:
            return False

        return self._wait_for((
            By.CSS_SELECTOR,
            '[data-purpose*="total-amount-summary"] span:nth-child(2)',
        )).text.startswith('0')
