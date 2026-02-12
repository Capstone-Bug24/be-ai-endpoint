from __future__ import annotations

from pathlib import Path
import json
from typing import Callable


class JsonlSpool:
    """Single-file durable queue for unsent events."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def append(self, event: dict) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False))
            f.write("\n")

    def size(self) -> int:
        if not self._path.exists():
            return 0
        lines = [line for line in self._path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return len(lines)

    def flush(self, send_fn: Callable[[dict], bool], batch_limit: int = 100) -> tuple[int, int]:
        if not self._path.exists():
            return 0, 0
        lines = [line for line in self._path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            self._path.unlink(missing_ok=True)
            return 0, 0

        sent = 0
        remaining: list[str] = []
        for idx, line in enumerate(lines):
            if sent >= batch_limit:
                remaining.extend(lines[idx:])
                break
            try:
                payload = json.loads(line)
            except Exception:
                # malformed line is dropped
                continue
            if send_fn(payload):
                sent += 1
                continue
            remaining.append(line)
            remaining.extend(lines[idx + 1 :])
            break

        if remaining:
            self._path.write_text("\n".join(remaining) + "\n", encoding="utf-8")
        else:
            self._path.unlink(missing_ok=True)
        return sent, len(remaining)
