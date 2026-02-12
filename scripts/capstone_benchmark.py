#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from capruntime.runtime import CameraRuntime
from capruntime.settings import (  # noqa: E402
    BackendSettings,
    ModelSettings,
    RuntimeSettings,
    SensorSettings,
    SourceSettings,
    SpoolSettings,
)


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])


def _run_case(
    case: str,
    source_file: Path,
    output_dir: Path,
    max_events: int,
    fps_limit: int,
    backend_url: str,
    dry_run: bool,
) -> dict:
    event_path = output_dir / f"{case}_events.jsonl"
    spool_path = output_dir / f"{case}_spool.jsonl"
    event_path.unlink(missing_ok=True)
    spool_path.unlink(missing_ok=True)

    settings = RuntimeSettings(
        site_id="S001",
        camera_id=f"bench_{case}",
        timezone="UTC",
        fps_limit=fps_limit,
        max_events=max_events,
        dry_run=dry_run,
        output_jsonl=str(event_path),
        source=SourceSettings(type="file", file_path=str(source_file), loop=True),
        model=ModelSettings(type="mock", score_threshold=0.25),
        sensors=[
            SensorSettings(name="s1", type="constant", interval_sec=0.05, constant_value=1.0),
            SensorSettings(name="s2", type="constant", interval_sec=0.10, constant_value=2.0),
        ],
        backend=BackendSettings(url=backend_url, timeout_sec=0.2),
        spool=SpoolSettings(file_path=str(spool_path), flush_batch=100),
    )

    runtime = CameraRuntime(settings)
    started = time.perf_counter()
    emitted = runtime.run()
    elapsed = time.perf_counter() - started

    event_lines = _count_jsonl(event_path)
    spool_lines = _count_jsonl(spool_path)
    throughput = 0.0 if elapsed <= 0 else emitted / elapsed
    return {
        "case": case,
        "dry_run": dry_run,
        "emitted_events": emitted,
        "jsonl_events": event_lines,
        "spool_events": spool_lines,
        "elapsed_sec": round(elapsed, 3),
        "events_per_sec": round(throughput, 2),
        "output_jsonl": str(event_path.relative_to(ROOT)),
        "spool_jsonl": str(spool_path.relative_to(ROOT)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="capstone runtime benchmark helper")
    parser.add_argument("--source-file", default="data/samples/sample.avi")
    parser.add_argument("--output-dir", default="outputs/bench")
    parser.add_argument("--max-events", type=int, default=400)
    parser.add_argument("--fps-limit", type=int, default=0)
    parser.add_argument("--report-json", default="outputs/bench/report.json")
    args = parser.parse_args()

    source_file = (ROOT / args.source_file).resolve()
    if not source_file.exists():
        raise FileNotFoundError(f"source file not found: {source_file}")
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": str(source_file.relative_to(ROOT)),
        "max_events": args.max_events,
        "fps_limit": args.fps_limit,
        "cases": [
            _run_case(
                case="dry_run",
                source_file=source_file,
                output_dir=output_dir,
                max_events=args.max_events,
                fps_limit=args.fps_limit,
                backend_url="http://127.0.0.1:8080/api/events",
                dry_run=True,
            ),
            _run_case(
                case="backend_down",
                source_file=source_file,
                output_dir=output_dir,
                max_events=args.max_events,
                fps_limit=args.fps_limit,
                backend_url="http://127.0.0.1:65500/api/events",
                dry_run=False,
            ),
        ],
    }

    report_path = (ROOT / args.report_json).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
