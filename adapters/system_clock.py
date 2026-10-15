"""Clock and token adapters backed by the standard library."""

import secrets
from datetime import datetime
from zoneinfo import ZoneInfo

from domain.models import Now

SAO_PAULO = ZoneInfo("America/Sao_Paulo")
TOKEN_BYTES = 32


class SystemClock:
    """Current instant in America/Sao_Paulo. Day 0 is Monday 0001-01-01, so ordinal - 1 is the domain day."""

    def now(self) -> Now:
        moment = datetime.now(SAO_PAULO)
        return Now(moment.toordinal() - 1, moment.hour * 60 + moment.minute)


class SecureTokens:
    def new_token(self) -> str:
        return secrets.token_urlsafe(TOKEN_BYTES)
