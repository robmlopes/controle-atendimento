from typing import Protocol


class TokenSource(Protocol):
    def new_token(self) -> str: ...
