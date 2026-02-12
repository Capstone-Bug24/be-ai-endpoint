# Architecture

## Runtime Model

- One process handles one camera stream.
- Sensor ingestion is parallelized by sensor workers in the same process.
- Main loop is intentionally single-threaded for video path simplicity.
- Horizontal scale is process-level (camera count = process count).

## Flow

1. Read frame from selected video source (`file|rtsp|webcam`)
2. Run model inference (`mock|yolo|onnx`)
3. Snapshot latest multi-sensor state
4. Build events
5. Emit to backend
6. If backend is unavailable, persist events to local spool
7. Flush spool opportunistically when backend recovers

## Reliability Rules

- Backend outage must not stop runtime execution.
- Sensor failure must not stop camera loop.
- RTSP source reconnect uses incremental backoff.
- Spool queue must preserve unsent events between retries.

## Ownership Boundary

- This repository scope is "camera/sensor to backend event runtime".
- Frontend visualization and backend policy/alert decisions are out of scope.

## Operational Contract

- Input contract: exactly one camera per process, optional many sensors.
- Output contract: event delivery attempts backend first, local spool fallback.
- Recovery contract: runtime continues through transient backend or RTSP faults.
