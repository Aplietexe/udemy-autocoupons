"""Entry point for the package."""
from __future__ import annotations

from asyncio import TaskGroup, run
from logging import getLogger
from threading import Thread

from aiohttp import ClientSession

from udemy_autocoupons.loggers import setup_loggers
from udemy_autocoupons.parse_arguments import parse_arguments
from udemy_autocoupons.persistent_data import (
    load_scrapers_data,
    save_scrapers_data,
)
from udemy_autocoupons.queue_manager import QueueManager
from udemy_autocoupons.run_driver import run_driver
from udemy_autocoupons.scrapers import scraper_types


async def main() -> None:
    """Uses all scrapers to get URLS and enrolls in the courses.

    Scrapers get urls asynchronously and send them to a queue, where they
    are then validated, parsed and sent to another queue, where a listening
    thread uses a WebDriver to enroll in all provided courses.

    """
    debug = getLogger("debug")
    scrapers_data = load_scrapers_data()

    debug.debug("Got scrapers data %s", scraper_types[0].__name__)

    args = parse_arguments()

    # Listen for urls in the async queue
    async with QueueManager() as (async_queue, mt_queue):
        # Listen for courses in the multithreading queue
        thread = Thread(
            target=run_driver,
            args=(mt_queue, args["profile_directory"], args["user_data_dir"]),
            name="UdemyDriverThread",
        )
        thread.start()
        debug.debug("UdemyDriverThread started")

        async with ClientSession() as client:
            scrapers = tuple(
                scraper_type(
                    async_queue,
                    client,
                    scrapers_data[scraper_type.__name__],
                )
                for scraper_type in scraper_types
            )

            async with TaskGroup() as task_group:
                # Start scrapers
                for scraper in scrapers:
                    task_group.create_task(scraper.scrap())
            # Wait for scrapers to finish
            debug.debug("All scrapers finished")
    # Wait for queues to finish
    # Wait for thread to finish
    debug.debug("Waiting for thread to finish")
    thread.join()

    save_scrapers_data(scrapers)


if __name__ == "__main__":
    setup_loggers()
    run(main())
