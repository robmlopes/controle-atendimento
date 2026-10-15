from typing import Protocol

from domain.models import Now


class Clock(Protocol):
    def now(self) -> Now: ...
