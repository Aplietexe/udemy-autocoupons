"""This module contains the QueueManager class."""
from __future__ import annotations

from asyncio import Queue as AsyncQueue, create_task
from logging import getLogger
from multiprocessing import JoinableQueue as MpQueue

from udemy_autocoupons.udemy_course import UdemyCourse

_debug = getLogger('debug')


class QueueManager:
    """A context manager for validating courses and interfacing between queues.

    It should be used as a async context manager.

    It uses an async Queue for scrapers to add their URLs, which is then
    accessed by the manager, which validates and parses the URL and adds the
    course to a multiprocessing JoinableQueue.

    On open it gives the async and multiprocessing queues, and on exit adds a
    None to each and waits for them to finish.

    Attributes:
      mp_queue: The wrapped multiprocessing queue.
      async_queue: The wrapper async queue.

    """

    def __init__(self) -> None:
        """Creates a queue and stores it in the queue attribute."""
        self.mp_queue: MpQueue[UdemyCourse | None] = MpQueue()  # pylint: disable=unsubscriptable-object
        self.async_queue: AsyncQueue[str | None] = AsyncQueue()

        self._seen: set[UdemyCourse] = set()
        self._task = create_task(self._process_courses())

    async def __aenter__(
        self,
    ) -> tuple[AsyncQueue[str | None], MpQueue[UdemyCourse | None]]:  # pylint: disable=unsubscriptable-object
        """Gets the queues.

        Returns:
            A tuple containing the async and multiprocessing queues.

        """
        _debug.debug('Entered QueueManager context manager')
        return (self.async_queue, self.mp_queue)

    async def __aexit__(self, *_) -> None:
        """Closes and waits the async and multiprocessing queue."""
        await self.async_queue.put(None)
        _debug.debug('Waiting async queue')
        await self.async_queue.join()

        _debug.debug('Waiting _process_courses task')
        await self._task

        self.mp_queue.put(None)
        _debug.debug('Waiting multiprocessing queue')
        self.mp_queue.join()

        _debug.debug('Exiting QueueManager context manager')

    async def _process_courses(self) -> None:
        while url := await self.async_queue.get():
            if course := UdemyCourse.from_url(url):
                if course not in self._seen:
                    self.mp_queue.put(course)
                else:
                    _debug.debug('Ignoring duplicate course %s', course)
            self.async_queue.task_done()

        _debug.debug('Got None in async queue')
        self.async_queue.task_done()
