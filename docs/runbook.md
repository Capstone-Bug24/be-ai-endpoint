# Runbook

## Prerequisites

- Python 3.11
- `pip install -r requirements.txt -r requirements-dev.txt`

## Basic Dry-run (File)

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

## Dual Camera Runtime

Use one process per camera:

```bash
PYTHONPATH=src CR_SPOOL_FILE_PATH=outputs/spool/cam1_pending.jsonl python -m capruntime --source-type rtsp --rtsp-url rtsp://127.0.0.1:8554/cam1 --camera-id cam01 --model-type mock --dry-run --output-jsonl outputs/cam1_events.jsonl --fps-limit 10
```

```bash
PYTHONPATH=src CR_SPOOL_FILE_PATH=outputs/spool/cam2_pending.jsonl python -m capruntime --source-type rtsp --rtsp-url rtsp://127.0.0.1:8554/cam2 --camera-id cam02 --model-type mock --dry-run --output-jsonl outputs/cam2_events.jsonl --fps-limit 10
```

## Backend Outage Behavior

- Unsent events are persisted to `outputs/spool/*.jsonl`.
- Backlog is flushed first on next successful send.

## Systemd Operation

Detailed steps: `docs/operations.md`

Core commands:

```bash
sudo systemctl enable --now capruntime@cam01
sudo systemctl enable --now capruntime@cam02
sudo journalctl -u capruntime@cam01 -f
```

## Demo And Validation

Scenario scripts and expected outcomes: `docs/demo_scenarios.md`

Performance baseline and repro: `docs/performance_report.md`

## Troubleshooting

- RTSP does not connect:
  - verify RTSP server (`mediamtx`) is running
  - verify camera URL and port
- spool keeps growing:
  - verify backend URL and backend health
  - verify firewall/network route to backend
- webcam open fails:
  - verify camera device permissions and index (`--camera-index`)

## Test

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
python scripts/test_hygiene.py --strict --max-duplicate-groups 0 --max-no-assert 0 --max-trivial-assert-true 0
```
