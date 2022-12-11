"""Entry point for the package."""
from __future__ import annotations

from asyncio import TaskGroup, run
from multiprocessing import JoinableQueue as MpQueue
from multiprocessing import Process

from aiohttp import ClientSession

from udemy_autocoupons.queue_manager import QueueManager
from udemy_autocoupons.scrapers import scraper_types
from udemy_autocoupons.udemy_course import UdemyCourse
from udemy_autocoupons.udemy_driver import UdemyDriver


def _run_driver(mp_queue: MpQueue[UdemyCourse | None]) -> None:  # pylint: disable=unsubscriptable-object
    """Starts a UdemyDriver and gives it the queue to enroll from it.

    Args:
        mp_queue: A multiprocessing queue to pass to the driver.

    """
    driver = UdemyDriver()
    driver.enroll_from_queue(mp_queue)


async def main() -> None:
    """Uses all scrapers to get URLS and enrolls in the courses.

    Scrapers get urls asynchronously and send them to a queue, where they
    are then validated, parsed and sent to another queue, where a listening
    process uses a WebDriver to enroll in all provided courses.

    """
    # Listen for urls in the async queue
    async with QueueManager() as (async_queue, mp_queue):
        # Listen for courses in the multiprocessing queue
        process = Process(target=_run_driver, args=(mp_queue,))
        process.start()

        async with ClientSession() as client:
            async with TaskGroup() as task_group:
                # Start scrapers
                for scraper_type in scraper_types:
                    scraper = scraper_type(
                        async_queue,
                        client,
                        None,
                    )
                    task_group.create_task(scraper.scrap())

            # Wait for scrappers to finish
    # Wait for queues to finish
    # Wait for process to finish
    process.join()


if __name__ == '__main__':
    run(main())
