# Runbook

## Prerequisites

- Python 3.11
- `pip install -r requirements.txt -r requirements-dev.txt`

## Basic Dry-run

```bash
PYTHONPATH=src python -m capruntime --config configs/runtime.yaml --dry-run --max-events 20
```

## Webcam

```bash
PYTHONPATH=src python -m capruntime --source-type webcam --camera-index 0 --dry-run
```

## RTSP

```bash
PYTHONPATH=src python -m capruntime \
  --source-type rtsp \
  --rtsp-url rtsp://127.0.0.1:8554/stream1 \
  --max-events 50
```

## Backend Outage Behavior

- Events are persisted to `outputs/spool/pending_events.jsonl` when backend send fails.
- On subsequent successful sends, backlog is flushed first.

## Test

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
python scripts/test_hygiene.py --strict --max-duplicate-groups 0 --max-no-assert 0 --max-trivial-assert-true 0
```
