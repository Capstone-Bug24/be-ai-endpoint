from __future__ import annotations

from pathlib import Path

from capruntime.runtime import CameraRuntime
from capruntime.settings import (
    BackendSettings,
    ModelSettings,
    RuntimeSettings,
    SensorSettings,
    SourceSettings,
    SpoolSettings,
)


def test_backend_down_events_are_spooled(sample_video: Path, tmp_path: Path) -> None:
    spool_file = tmp_path / "pending.jsonl"
    settings = RuntimeSettings(
        site_id="S001",
        camera_id="cam01",
        fps_limit=0,
        max_events=4,
        dry_run=False,
        output_jsonl=None,
        source=SourceSettings(type="file", file_path=str(sample_video), loop=False),
        model=ModelSettings(type="mock"),
        sensors=[SensorSettings(name="s1", type="constant", interval_sec=0.01, constant_value=1.0)],
        backend=BackendSettings(url="http://127.0.0.1:65500/api/events", timeout_sec=0.05),
        spool=SpoolSettings(file_path=str(spool_file), flush_batch=50),
    )

    runtime = CameraRuntime(settings)
    emitted = runtime.run()
    assert emitted == 4
    assert spool_file.exists()
    assert len([line for line in spool_file.read_text(encoding="utf-8").splitlines() if line.strip()]) >= 4
