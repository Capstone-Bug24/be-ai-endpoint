# Architecture

## Runtime Model

- One process handles one camera stream.
- Sensor ingestion is parallelized by sensor workers in the same process.
- Main loop is intentionally single-threaded for video path simplicity.

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
