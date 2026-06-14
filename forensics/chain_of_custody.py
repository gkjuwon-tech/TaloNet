"""Chain-of-custody record and append-only custody log.

Integrity is the whole point of forensics, so this is a working (stdlib-only)
append-only log that hash-chains each event to the previous one (tamper-evident),
mirroring the procedure in ``docs/08_사후_포렌식.md`` §3. The pipeline records
every stage here; the report bundles the log as an appendix.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CustodyEvent:
    """One immutable entry in the custody log (a hand-over or examination)."""

    timestamp: str
    actor: str  # who performed/received
    action: str  # "intake" | "imaging" | "transfer" | "examination" | "seal"
    detail: str
    witness: str = ""  # two-person integrity
    prev_hash: str = ""  # hash of the previous event (chain link)
    entry_hash: str = ""  # hash of THIS event incl. prev_hash

    def compute_hash(self) -> str:
        payload = {
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action": self.action,
            "detail": self.detail,
            "witness": self.witness,
            "prev_hash": self.prev_hash,
        }
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ChainOfCustody:
    """Append-only, hash-chained custody log for one evidence item.

    Each appended event embeds the hash of the prior event, so any later edit
    breaks the chain and :meth:`verify` returns ``False``. This is a
    tamper-*evident* audit trail, not access control.
    """

    def __init__(self, evidence_id: str) -> None:
        self.evidence_id = evidence_id
        self._events: list[CustodyEvent] = []

    def record(
        self,
        actor: str,
        action: str,
        detail: str,
        witness: str = "",
    ) -> CustodyEvent:
        """Append a new custody event, chaining it to the previous one."""
        prev_hash = self._events[-1].entry_hash if self._events else ""
        event = CustodyEvent(
            timestamp=_utc_now(),
            actor=actor,
            action=action,
            detail=detail,
            witness=witness,
            prev_hash=prev_hash,
        )
        event.entry_hash = event.compute_hash()
        self._events.append(event)
        return event

    def verify(self) -> bool:
        """Re-walk the chain; True iff every link and hash is intact."""
        prev_hash = ""
        for event in self._events:
            if event.prev_hash != prev_hash:
                return False
            if event.entry_hash != event.compute_hash():
                return False
            prev_hash = event.entry_hash
        return True

    def to_log(self) -> list[dict[str, str]]:
        """Export the log (e.g. for the report appendix)."""
        return [asdict(event) for event in self._events]

    @property
    def events(self) -> list[CustodyEvent]:
        return list(self._events)
