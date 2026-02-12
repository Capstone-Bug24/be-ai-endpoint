from __future__ import annotations

from pathlib import Path
import json
import logging

import requests

from .settings import BackendSettings, SpoolSettings
from .spool import JsonlSpool

logger = logging.getLogger(__name__)


class BackendEmitter:
    def __init__(self, backend: BackendSettings) -> None:
        self._url = backend.url
        self._timeout = backend.timeout_sec

    def send(self, event: dict) -> bool:
        try:
            response = requests.post(self._url, json=event, timeout=self._timeout)
            return 200 <= response.status_code < 300
        except Exception:
            return False


class ResilientEmitter:
    def __init__(
        self,
        backend: BackendSettings,
        spool: SpoolSettings,
        dry_run: bool = True,
        output_jsonl: str | None = None,
    ) -> None:
        self._backend = BackendEmitter(backend)
        self._spool = JsonlSpool(spool.file_path)
        self._flush_batch = spool.flush_batch
        self._dry_run = dry_run
        self._out_file: Path | None = Path(output_jsonl) if output_jsonl else None
        if self._out_file:
            self._out_file.parent.mkdir(parents=True, exist_ok=True)

    def _write_jsonl(self, event: dict) -> None:
        if self._out_file is None:
            return
        with self._out_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False))
            f.write("\n")

    def emit(self, event: dict) -> bool:
        self._write_jsonl(event)

        if self._dry_run:
            logger.info("DRY_RUN event=%s", event.get("event_id"))
            return True

        # Flush old backlog first to preserve order as much as possible.
        self._spool.flush(self._backend.send, batch_limit=self._flush_batch)
        ok = self._backend.send(event)
        if ok:
            return True
        self._spool.append(event)
        return False

    @property
    def pending_spool_size(self) -> int:
        return self._spool.size()

    def close(self) -> None:
        if self._dry_run:
            return
        self._spool.flush(self._backend.send, batch_limit=self._flush_batch)
