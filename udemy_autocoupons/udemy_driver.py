"""This module contains the UdemyDriver class."""
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC  # noqa: N812
from selenium.webdriver.support.wait import WebDriverWait

from udemy_autocoupons.constants import WAIT_POLL_FREQUENCY, WAIT_TIMEOUT


class UdemyDriver:
    """Handles Udemy usage."""

    def __init__(self, email: str, password: str) -> None:
        """Starts the driver and logs in.

        Args:
            email: Email address of the account
            password: Password of the account

        """
        options = uc.ChromeOptions()
        options.add_argument('--start-maximized')
        self.driver = uc.Chrome(options=options)

        self._wait = WebDriverWait(
            self.driver,
            WAIT_TIMEOUT,
            WAIT_POLL_FREQUENCY,
        )

        self._login(email, password)

    def _wait_for(self, locator: tuple[str, str]) -> WebElement:
        return self._wait.until(EC.presence_of_element_located(locator))

    def _login(self, email: str, password: str) -> None:
        """Makes the driver log in to the given Udemy account.

        Args:
            email: Email address of the account
            password: Password of the account

        """
        self.driver.get('https://www.udemy.com/join/login-popup/')

        email_input = self._wait_for((By.NAME, 'email'))
        email_input.send_keys(email)

        password_input = self.driver.find_element(By.NAME, 'password')
        password_input.send_keys(password)

        self.driver.find_element(
            By.CSS_SELECTOR,
            'button[class*="auth-udemy--submit-button"]',
        ).click()

        self._wait.until(lambda driver: 'login' not in driver.current_url)
