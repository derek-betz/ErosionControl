"""Session log helpers for duplicate avoidance."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class SessionLog:
    """Track processed contracts across runs."""

    path: Path = field(default_factory=lambda: Path("ec_train_sessions.jsonl"))

    def load(self) -> set[str]:
        """Load seen contract numbers."""
        if not self.path.exists():
            return set()
        seen: set[str] = set()
        with self.path.open() as f:
            for line in f:
                try:
                    record = json.loads(line)
                    contract = record.get("contract")
                    if contract:
                        seen.add(str(contract))
                except json.JSONDecodeError:
                    continue
        return seen

    def append(self, contracts: Iterable[str]) -> None:
        """Persist new contract numbers."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            for contract in contracts:
                f.write(json.dumps({"contract": contract}) + "\n")


__all__ = ["SessionLog"]
