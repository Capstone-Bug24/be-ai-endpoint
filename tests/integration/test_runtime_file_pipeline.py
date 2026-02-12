from __future__ import annotations

from pathlib import Path
import json

from capruntime.runtime import CameraRuntime
from capruntime.settings import (
    BackendSettings,
    ModelSettings,
    RuntimeSettings,
    SourceSettings,
    SpoolSettings,
)


def _read_jsonl(path: Path) -> list[dict]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(line) for line in lines]


def test_runtime_emits_events_to_jsonl(sample_video: Path, tmp_path: Path) -> None:
    out_file = tmp_path / "events.jsonl"
    settings = RuntimeSettings(
        site_id="S001",
        camera_id="cam01",
        fps_limit=0,
        max_events=5,
        dry_run=True,
        output_jsonl=str(out_file),
        source=SourceSettings(type="file", file_path=str(sample_video), loop=False),
        model=ModelSettings(type="mock"),
        sensors=[],
        backend=BackendSettings(url="http://127.0.0.1:9999/api/events", timeout_sec=0.2),
        spool=SpoolSettings(file_path=str(tmp_path / "spool.jsonl"), flush_batch=100),
    )

    runtime = CameraRuntime(settings)
    emitted = runtime.run()
    assert emitted == 5
    events = _read_jsonl(out_file)
    assert len(events) == 5
    assert events[0]["camera_id"] == "cam01"
    assert "sensors" in events[0]
