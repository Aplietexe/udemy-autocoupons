"""This module contains representations of the possible stats of a course."""

from enum import Enum
from typing import Literal


class State(Enum):
    """The possible states of a course along and after the enrolling process."""
    ENROLLABLE = 'ENROLLABLE'
    ENROLLED = 'ENROLLED'
    ERROR = 'ERROR'
    PAID = 'PAID'
    TO_BLACKLIST = 'TO_BLACKLIST'


DoneT = Literal[State.ENROLLED, State.PAID, State.TO_BLACKLIST]

DoneOrErrorT = DoneT | Literal[State.ERROR]
