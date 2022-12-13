"""This module contains representations of the possible stats of a course."""

from enum import Enum
from typing import Literal


class State(Enum):
    """The possible states of a course along and after the enrolling process."""
    ENROLLABLE = 'ENROLLABLE'
    ENROLLED = 'ENROLLED'
    ERROR = 'ERROR'
    FREE = 'FREE'
    IN_ACCOUNT = 'IN_ACCOUNT'
    PAID = 'PAID'
    UNAVAILABLE = 'UNAVAILABLE'


DoneT = Literal[State.ENROLLED,
                State.FREE,
                State.IN_ACCOUNT,
                State.PAID,
                State.UNAVAILABLE,
               ]

DoneOrErrorT = DoneT | Literal[State.ERROR]
