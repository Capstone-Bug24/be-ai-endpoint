# AI Runtime Shared Schema Examples

This document shows the final event contract shape used by `be-ai-endpoint`.

## Event JSON

```json
{
  "event_id": "9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21",
  "ts": "2026-05-06T09:21:10.320Z",
  "site_id": "S001",
  "camera_id": "cam01",
  "frame_id": 2017,
  "frame_ts": "2026-05-06T09:21:10.290Z",
  "event_type": "PROXIMITY_RISK",
  "event_status": "ACTIVE",
  "object_type": "PERSON",
  "severity": "HIGH",
  "track_id": 15,
  "confidence": 0.91,
  "bbox": {
    "x1": 320,
    "y1": 140,
    "x2": 590,
    "y2": 610
  },
  "zone": {
    "zone_id": "danger_q2",
    "inside": true
  },
  "reason": {
    "code": "PROXIMITY_RISK",
    "factors": [
      "PERSON_DETECTED",
      "ZONE_INTRUSION",
      "ULTRA_FRONT_ALERT"
    ]
  },
  "sensors": {
    "ultra_front": {
      "id": "ultra_front_01",
      "type": "ultrasonic",
      "ts": "2026-05-06T09:21:10.100Z",
      "status": "ALERT",
      "unit": "m",
      "value": 1.42
    },
    "ultra_rear": {
      "id": "ultra_rear_01",
      "type": "ultrasonic",
      "ts": "2026-05-06T09:21:10.100Z",
      "status": "OK",
      "unit": "m",
      "value": 2.35
    },
    "temperature": {
      "id": "temp_01",
      "type": "temperature",
      "ts": "2026-05-06T09:21:09.950Z",
      "status": "OK",
      "unit": "celsius",
      "value": 28.3
    }
  }
}
```

## Backend Request

```http
POST /api/ai/events HTTP/1.1
Content-Type: application/json
```

The request body is one event JSON object. The `sensors` field is a map keyed by sensor name. Each sensor keeps its own `status`; there is no top-level `sensor_status`.

## Sensor Status Values

- `OK`: sensor value is normal
- `WARN`: sensor requires attention
- `ALERT`: dangerous sensor value
- `CRITICAL`: immediate response needed
- `STALE`: latest reading is too old
- `OFFLINE`: sensor is unavailable
- `UNKNOWN`: status cannot be determined

## RTSP Registry Example

| camera_id | rtsp_url | codec | fps | resolution | owner | healthcheck |
|---|---|---|---:|---|---|---|
| `cam01` | `rtsp://stream-host:8554/cam1` | `H264` | 10 | `1280x720` | Streaming team | `ffprobe rtsp://stream-host:8554/cam1` |
| `cam02` | `rtsp://stream-host:8554/cam2` | `H264` | 10 | `1280x720` | Streaming team | `ffprobe rtsp://stream-host:8554/cam2` |
