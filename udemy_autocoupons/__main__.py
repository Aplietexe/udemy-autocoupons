"""Entry point for the package."""
from __future__ import annotations

from asyncio import TaskGroup, run
from logging import getLogger
from queue import Queue as MtQueue
from threading import Event, Thread

from aiohttp import ClientSession
from dotenv import load_dotenv

from udemy_autocoupons.loggers import setup_loggers
from udemy_autocoupons.parse_arguments import parse_arguments
from udemy_autocoupons.persistent_data import (
    load_courses_store,
    load_errors,
    load_scrapers_data,
    save_courses_store,
    save_errors,
    save_scrapers_data,
)
from udemy_autocoupons.queue_manager import QueueManager
from udemy_autocoupons.run_driver import run_driver
from udemy_autocoupons.scrapers import ScrapersT, scraper_types
from udemy_autocoupons.setup.setup_telegram import setup_telegram


async def main() -> None:
    """Uses all scrapers to get URLS and enrolls in the courses.

    Scrapers get urls asynchronously and send them to a queue, where they
    are then validated, parsed and sent to another queue, where a listening
    thread uses a WebDriver to enroll in all provided courses.

    """
    debug = getLogger("debug")
    printer = getLogger("printer")
    args = parse_arguments()

    if args["setup"] == "telegram":
        await setup_telegram()
        return

    scrapers_data = load_scrapers_data()
    courses_store = load_courses_store()
    errors = load_errors()

    debug.debug("Got scrapers data %s", scraper_types[0].__name__)

    stop_event = Event()

    # Listen for urls in the async queue
    async with QueueManager(courses_store, stop_event) as (
        async_queue,
        mt_queue,
    ):
        for error in errors:
            mt_queue.put(error)

        printer.info("Reattempting %s previously failed courses", len(errors))
        new_errors_queue = MtQueue()

        # Listen for courses in the multithreading queue
        thread = Thread(
            target=run_driver,
            args=(
                mt_queue,
                courses_store,
                new_errors_queue,
                stop_event,
                args["profile_directory"],
                args["user_data_dir"],
            ),
            name="UdemyDriverThread",
            daemon=True,
        )
        thread.start()
        debug.debug("UdemyDriverThread started")

        async with ClientSession() as client:
            scrapers: ScrapersT = tuple(
                scraper_type(
                    async_queue,
                    client,
                    scrapers_data[scraper_type.__name__],
                    stop_event,
                )
                for scraper_type in scraper_types
            )  # type: ignore

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

    errors.clear()
    while not new_errors_queue.empty():
        errors.append(new_errors_queue.get())
    save_scrapers_data(scrapers)
    save_courses_store(courses_store)
    save_errors(errors)

    printer.info(
        "Finished run. %s courses will be reattempted on next run",
        len(errors),
    )


if __name__ == "__main__":
    load_dotenv()
    setup_loggers()
    run(main())
