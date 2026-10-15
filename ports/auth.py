from typing import Protocol

from domain.auth import Owner, SessionInfo


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...


class OwnerRead(Protocol):
    def owner_by_email(self, email: str) -> Owner | None: ...

    def owner_by_professional(self, business_id: int, professional_id: int) -> Owner | None: ...


class OwnerWrite(Protocol):
    def add_owner(
        self,
        business_id: int,
        email: str,
        password_hash: str,
        role: str = "owner",
        professional_id: int | None = None,
    ) -> Owner: ...


class SessionStore(Protocol):
    """Sessions are looked up by the raw token; implementations must persist only a hash of it."""

    def create(self, owner: Owner, token: str, csrf_token: str, created_total: int) -> None: ...

    def get(self, token: str) -> SessionInfo | None: ...

    def delete(self, token: str) -> None: ...


class LoginAttempts(Protocol):
    def record_failure(self, key: str, at_total: int) -> None: ...

    def failures_since(self, key: str, since_total: int) -> int: ...

    def clear(self, key: str) -> None: ...
