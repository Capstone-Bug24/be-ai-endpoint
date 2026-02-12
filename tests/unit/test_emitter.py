from __future__ import annotations

from pathlib import Path

from capruntime.emitter import ResilientEmitter
from capruntime.settings import BackendSettings, SpoolSettings


def test_dry_run_keeps_spool_empty(tmp_path: Path) -> None:
    spool_file = tmp_path / "spool.jsonl"
    emitter = ResilientEmitter(
        backend=BackendSettings(url="http://127.0.0.1:65500/api/events", timeout_sec=0.01),
        spool=SpoolSettings(file_path=str(spool_file), flush_batch=100),
        dry_run=True,
        output_jsonl=None,
    )
    ok = emitter.emit({"event_id": "e1"})
    assert ok is True
    assert emitter.pending_spool_size == 0


def test_backend_failure_spools_event(tmp_path: Path) -> None:
    spool_file = tmp_path / "spool.jsonl"
    emitter = ResilientEmitter(
        backend=BackendSettings(url="http://127.0.0.1:65500/api/events", timeout_sec=0.01),
        spool=SpoolSettings(file_path=str(spool_file), flush_batch=100),
        dry_run=False,
        output_jsonl=None,
    )
    ok = emitter.emit({"event_id": "e1"})
    assert ok is False
    assert emitter.pending_spool_size == 1
