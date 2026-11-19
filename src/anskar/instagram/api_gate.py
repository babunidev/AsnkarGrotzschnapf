"""Stop Instagram Graph calls after Meta rate-limit or API-access blocks.

Ported from Azeroth Moments' InstagramApiGate. Meta's app-level limits and
"API access blocked" apply to the whole app — keep polling/retrying only makes
it worse. Survives process restarts via SQLite control rows.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from anskar.instagram.errors import InstagramError
from anskar.instagram.ledger import connect as ledger_connect, ledger_path

KEY_UNTIL = "instagram_api_cooldown_until"
KEY_REASON = "instagram_api_cooldown_reason"
KEY_STRIKES = "instagram_api_cooldown_strikes"
KEY_ACCESS_BLOCKED = "instagram_api_access_blocked"
KEY_ACCESS_REASON = "instagram_api_access_reason"
KEY_ACCESS_STATUS = "instagram_api_access_status"
KEY_ACCESS_CHECKED_AT = "instagram_api_access_checked_at"

DEFAULT_COOLDOWN_SECONDS = 300.0
MAX_COOLDOWN_SECONDS = 3600.0
STRIKE_RESET_AFTER = 7200.0

CONTROL_SCHEMA = """
CREATE TABLE IF NOT EXISTS control (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class InstagramApiGate:
    def __init__(self, database: Path | None = None) -> None:
        self.path = database or ledger_path()

    def remaining(self, *, now: float | None = None) -> float:
        now = time.time() if now is None else now
        if self.access_blocked():
            return 86400.0
        return max(0.0, self._until() - now)

    def blocked(self, *, now: float | None = None) -> bool:
        return self.access_blocked() or self.rate_limited(now=now)

    def rate_limited(self, *, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        return self._until() > now

    def access_blocked(self) -> bool:
        return self._get(KEY_ACCESS_BLOCKED, "0") == "1"

    def reason(self) -> str:
        if self.access_blocked():
            return self._get(KEY_ACCESS_REASON, "") or "API access blocked"
        return self._get(KEY_REASON, "")

    def assert_clear(self) -> None:
        """Raise before any live Graph publish/poll when the gate is closed."""
        if self.access_blocked():
            raise InstagramError(
                "Meta API access is marked blocked locally after an earlier "
                f"refusal ({self.reason()}). Fix access in the Meta developer "
                "dashboard, then run `anskar instagram status` to clear the gate. "
                "No further Instagram Graph calls were made.",
                kind="access_blocked",
            )
        remaining = self.remaining()
        if remaining > 0:
            raise InstagramError(
                f"Instagram API is in a local cooldown for {int(remaining)}s "
                f"after a rate limit ({self.reason() or 'rate limited'}). "
                "No further Graph calls were made.",
                kind="rate_limit",
            )

    def trip_rate_limit(
        self,
        *,
        retry_after: float | None = None,
        detail: str = "",
        now: float | None = None,
    ) -> float:
        now = time.time() if now is None else now
        until = self._until()
        strikes = self._strikes()
        if until > now:
            strikes += 1
        elif now - until > STRIKE_RESET_AFTER:
            strikes = 1
        else:
            strikes += 1
        base = max(float(retry_after or 0), DEFAULT_COOLDOWN_SECONDS)
        cooldown = min(MAX_COOLDOWN_SECONDS, base * (2 ** max(0, strikes - 1)))
        new_until = max(until, now + cooldown)
        reason = detail or "Application request limit reached"
        self._set(KEY_UNTIL, str(new_until))
        self._set(KEY_REASON, reason[:400])
        self._set(KEY_STRIKES, str(strikes))
        return new_until - now

    def trip_access_blocked(self, *, detail: str = "", now: float | None = None) -> None:
        now = time.time() if now is None else now
        reason = detail or "API access blocked"
        self._set(KEY_ACCESS_BLOCKED, "1")
        self._set(KEY_ACCESS_REASON, reason[:400])
        self._set(KEY_ACCESS_STATUS, "blocked")
        self._set(KEY_ACCESS_CHECKED_AT, str(now))

    def record_access_ok(self, *, detail: str = "", now: float | None = None) -> None:
        now = time.time() if now is None else now
        self._set(KEY_ACCESS_BLOCKED, "0")
        self._set(KEY_ACCESS_STATUS, "ok")
        self._set(KEY_ACCESS_CHECKED_AT, str(now))
        self._set(KEY_ACCESS_REASON, (detail or "")[:400])

    def note_error(self, exc: InstagramError) -> None:
        """Update the gate from a classified Graph error."""
        if exc.kind == "access_blocked":
            self.trip_access_blocked(detail=str(exc))
        elif exc.kind == "rate_limit":
            self.trip_rate_limit(detail=str(exc))

    def snapshot(self) -> dict[str, object]:
        remaining = self.remaining()
        return {
            "blocked": self.blocked(),
            "access_blocked": self.access_blocked(),
            "rate_limited": self.rate_limited(),
            "remaining_seconds": round(remaining, 1),
            "reason": self.reason(),
            "api_access_status": self._get(KEY_ACCESS_STATUS, "") or "unverified",
        }

    def _until(self) -> float:
        try:
            return float(self._get(KEY_UNTIL, "0") or 0)
        except ValueError:
            return 0.0

    def _strikes(self) -> int:
        try:
            return max(0, int(self._get(KEY_STRIKES, "0") or 0))
        except ValueError:
            return 0

    def _get(self, key: str, default: str) -> str:
        with ledger_connect(self.path) as connection:
            _ensure_control(connection)
            row = connection.execute(
                "SELECT value FROM control WHERE key = ?", (key,)
            ).fetchone()
        return str(row["value"]) if row is not None else default

    def _set(self, key: str, value: str) -> None:
        with ledger_connect(self.path) as connection:
            _ensure_control(connection)
            connection.execute(
                """
                INSERT INTO control (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )


def _ensure_control(connection: sqlite3.Connection) -> None:
    connection.executescript(CONTROL_SCHEMA)
