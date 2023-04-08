"""This module contains a thread-safe list-like collection."""

from collections.abc import Iterator, MutableSequence
from threading import Lock
from typing import Generic, TypeVar

_ItemT = TypeVar("_ItemT")


class ThreadSafeList(MutableSequence, Generic[_ItemT]):
    """A thread-safe list-like collection."""

    def __init__(self, initial_items: list[_ItemT] | None = None) -> None:
        """A thread-safe list-like collection.

        Args:
            initial_items: The initial items.

        """
        self._list = initial_items or []
        self._lock = Lock()

    def __len__(self) -> int:
        """Returns the length of the list."""
        with self._lock:
            return len(self._list)

    def __getitem__(self, index: int) -> _ItemT:
        """Returns the item at the given index."""
        with self._lock:
            return self._list[index]

    def __setitem__(self, index: int, new_item: _ItemT) -> None:
        """Sets the item at the given index."""
        with self._lock:
            self._list[index] = new_item

    def __delitem__(self, index: int) -> None:
        """Deletes the item at the given index."""
        with self._lock:
            self._list.pop(index)

    def __contains__(self, testing_item: _ItemT) -> bool:
        """Returns True if the item is in the list."""
        with self._lock:
            return testing_item in self._list

    def to_list(self) -> list[_ItemT]:
        """Returns a copy of the content as a Python list."""
        with self._lock:
            return self._list.copy()

    def insert(self, index: int, new_item: _ItemT) -> None:
        """Inserts the item at the given index."""
        with self._lock:
            self._list.insert(index, new_item)

    def __iter__(self) -> Iterator[_ItemT]:
        """Returns an iterator over the items."""
        with self._lock:
            return iter(self._list)

    def __reversed__(self) -> Iterator[_ItemT]:
        """Returns a reversed iterator over the items."""
        with self._lock:
            return reversed(self._list)

    def __repr__(self) -> str:
        """Returns a string representation of the list."""
        with self._lock:
            return repr(self._list)

    def append(self, new_item: _ItemT) -> None:
        """Appends the item to the list."""
        with self._lock:
            self._list.append(new_item)

    def extend(self, new_items: list[_ItemT]) -> None:
        """Extends the list with the given items."""
        with self._lock:
            self._list.extend(new_items)

    def pop(self, index: int = -1) -> _ItemT:
        """Pops the item at the given index."""
        with self._lock:
            return self._list.pop(index)

    def remove(self, to_remove: _ItemT) -> None:
        """Removes the first occurrence of the item."""
        with self._lock:
            self._list.remove(to_remove)

    def clear(self) -> None:
        """Clears the list."""
        with self._lock:
            self._list.clear()
