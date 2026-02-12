# Performance And Resilience Report

## Benchmark Baseline

- generated at (UTC): `2026-02-12T09:40:20.536827+00:00`
- source file: `data/samples/sample.avi`
- model: `mock`
- sensors: 2 constant sensors
- run profile: `max_events=400`, `fps_limit=0`

## Results

| Case | dry_run | emitted_events | elapsed_sec | events_per_sec | spool_events |
|---|---:|---:|---:|---:|---:|
| dry_run | true | 400 | 0.201 | 1993.32 | 0 |
| backend_down | false | 400 | 0.904 | 442.41 | 400 |

## Interpretation

- Runtime keeps processing while backend is unavailable.
- Backend failure path is slower due to HTTP timeout + spool write overhead.
- Event loss was not observed in baseline run (spool captured all unsent events).

## Reproduce

```bash
cd ~/CapstoneProjects/be-ai-endpoint
PYTHONPATH=src python3 scripts/capstone_benchmark.py --max-events 400 --fps-limit 0
cat outputs/bench/report.json
```

## Limits

- This benchmark uses file input and mock model; it is not a field-accuracy test.
- RTSP network jitter and real model latency must be validated separately on target hardware.
