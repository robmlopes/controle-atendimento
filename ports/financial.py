from typing import Protocol

from domain.models import FinancialSummary, MovementItem


class FinancialRead(Protocol):
    """Calculates balances, commissions and daily ledger for a business or a specific professional."""

    def statement(
        self, business_id: int, from_day: int, to_day: int, professional_id: int | None = None
    ) -> tuple[MovementItem, ...]: ...

    def summary(
        self, business_id: int, from_day: int, to_day: int, professional_id: int | None = None
    ) -> FinancialSummary: ...
