"""This module contains the QueueManager class."""
from __future__ import annotations

from asyncio import Queue as AsyncQueue, create_task
from logging import getLogger
from queue import Queue as MtQueue

from udemy_autocoupons.courses_store import CoursesStore
from udemy_autocoupons.udemy_course import CourseWithCoupon

_debug = getLogger("debug")


class QueueManager:
    """A context manager for validating courses and interfacing between queues.

    It should be used as a async context manager.

    It uses an async Queue for scrapers to add their URLs, which is then
    accessed by the manager, which validates and parses the URL and adds the
    course to a multithreading JoinableQueue.

    On open it gives the async and multithreading queues, and on exit adds a
    None to each and waits for them to finish.

    Attributes:
      mt_queue: The wrapped multithreading queue.
      async_queue: The wrapper async queue.

    """

    def __init__(self, courses_store: CoursesStore) -> None:
        """Creates a queue and stores it in the queue attribute."""
        self.mt_queue: MtQueue[CourseWithCoupon | None] = MtQueue()
        self.async_queue: AsyncQueue[str | None] = AsyncQueue()

        self._courses_store = courses_store
        self._task = create_task(self._process_courses())

    async def __aenter__(
        self,
    ) -> tuple[AsyncQueue[str | None], MtQueue[CourseWithCoupon | None]]:
        """Gets the queues.

        Returns:
            A tuple containing the async and multithreading queues.

        """
        _debug.debug("Entered QueueManager context manager")
        return (self.async_queue, self.mt_queue)

    async def __aexit__(self, exc_type: type[BaseException] | None, *_) -> None:
        """Closes and waits the async and multithreading queue."""
        if exc_type:
            return

        await self.async_queue.put(None)
        _debug.debug("Waiting async queue")
        await self.async_queue.join()

        _debug.debug("Waiting _process_courses task")
        await self._task

        self.mt_queue.put(None)
        _debug.debug("Waiting multithreading queue")
        self.mt_queue.join()

        _debug.debug("Exiting QueueManager context manager")

    async def _process_courses(self) -> None:
        while url := await self.async_queue.get():
            if course := CourseWithCoupon.from_url(url):
                if course not in self._courses_store:
                    self.mt_queue.put(course)
                else:
                    _debug.debug("Ignoring duplicate course %s", course)
            self.async_queue.task_done()

        _debug.debug("Got None in async queue")
        self.async_queue.task_done()
