# Handoff Prompt (be-ai-endpoint)

Last updated: 2026-02-12

## Runtime V2 Intent

This repository now uses a rebuilt runtime architecture under `src/capruntime`:

- one process = one camera
- many sensors per process (independent sensor workers)
- resilient backend delivery via local spool queue
- internal model switch (`mock|yolo|onnx`), no dynamic plugin loading

## Active Entry

- CLI: `python -m capruntime`
- Config: `configs/runtime.yaml`

## Code Layout

- `src/capruntime/settings.py` config and env merge
- `src/capruntime/video.py` file/webcam/rtsp sources
- `src/capruntime/sensors.py` sensor workers and snapshot hub
- `src/capruntime/model.py` internal model runners
- `src/capruntime/events.py` event schema builder
- `src/capruntime/spool.py` durable jsonl queue
- `src/capruntime/emitter.py` backend emitter + spool fallback
- `src/capruntime/runtime.py` main camera loop

## Legacy Status

Old implementation files were removed from this active repository snapshot.
New work must stay in runtime v2 structure.

## Rules

- Keep active changes in `src/capruntime` and `tests`.
- Avoid reintroducing plugin-path runtime loading.
- Keep behavior explicit and operationally testable.
- If behavior changes, update `README.md`, `docs/index.md`, and tests together.
- Keep operations docs aligned: `docs/operations.md`, `docs/demo_scenarios.md`, `docs/performance_report.md`.

## Capstone Acceptance Focus

- one process per camera
- multi-sensor in one process
- backend-down spool survival
- RTSP reconnect survival
- systemd deployment readiness

## Verification

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
python scripts/test_hygiene.py --strict --max-duplicate-groups 0 --max-no-assert 0 --max-trivial-assert-true 0
```
