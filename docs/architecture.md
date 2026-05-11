# Architecture

## Runtime Model

- One process handles one camera stream.
- Sensor ingestion is parallelized by sensor workers in the same process.
- Main loop is intentionally single-threaded for video path simplicity.
- Horizontal scale is process-level: camera count equals runtime process count.

## Flow

1. Read frame from selected video source (`file|rtsp|webcam`).
2. Run model inference (`mock|yolo|onnx`).
3. Snapshot latest multi-sensor state.
4. Apply baseline rules for zone/sensor fusion and emit top-level zone match results.
5. Build one frame analysis payload for the frame.
6. Emit to backend via `POST /api/ai/events`.
7. If backend is unavailable, persist payloads to local spool.
8. Flush spool opportunistically when backend recovers.

## Output Shape

The current runtime output is frame-based:

```text
analysis_id + zones[] + detections[] + zone_matches[] + sensors + alerts[]
```

This replaced the older one-event-per-object shape for cross-team integration because one frame can contain multiple people/objects.

## Reliability Rules

- Backend outage must not stop runtime execution.
- Sensor failure must not stop camera loop.
- RTSP source reconnect uses incremental backoff.
- Spool queue must preserve unsent payloads between retries.

## Ownership Boundary

- This repository scope is camera/sensor input to backend frame analysis delivery.
- Frontend visualization and backend final alert policy are out of scope.
- Current zone/sensor rules are baseline logic, not the final industrial safety policy; `zones[]` defines areas and `zone_matches[]` records detection-zone results.

## Operational Contract

- Input contract: exactly one camera per process, optional many sensors.
- Output contract: frame analysis delivery attempts backend first, local spool fallback.
- Recovery contract: runtime continues through transient backend or RTSP faults.
