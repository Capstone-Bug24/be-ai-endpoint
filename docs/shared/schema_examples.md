# AI Runtime Shared Schema Examples

This document is the current shared API contract for `be-ai-endpoint`.
The current contract is frame-based: one analyzed frame produces one JSON payload.

## Frame Analysis JSON

```json
{
  "analysis_id": "9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21",
  "ts": "2026-05-11T12:00:00.120Z",
  "site_id": "S001",
  "camera_id": "cam01",
  "frame_id": 318,
  "frame_ts": "2026-05-11T12:00:00.000Z",
  "frame_width": 1920,
  "frame_height": 1080,
  "zones": [
    {
      "zone_id": "danger_q2",
      "name": "위험구역 2",
      "zone_type": "polygon",
      "severity": "HIGH",
      "points_norm": [
        { "x": 0.0, "y": 0.0 },
        { "x": 0.5, "y": 0.0 },
        { "x": 0.5, "y": 0.5 },
        { "x": 0.0, "y": 0.5 }
      ]
    },
    {
      "zone_id": "forklift_lane",
      "name": "지게차 이동 구역",
      "zone_type": "polygon",
      "severity": "HIGH",
      "points_norm": [
        { "x": 0.12, "y": 0.2 },
        { "x": 0.48, "y": 0.18 },
        { "x": 0.55, "y": 0.72 },
        { "x": 0.10, "y": 0.76 }
      ]
    }
  ],
  "detections": [
    {
      "detection_id": "9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21:det-1",
      "object_type": "PERSON",
      "confidence": 0.91,
      "track_id": null,
      "bbox": {
        "x1": 152,
        "y1": 156,
        "x2": 419,
        "y2": 902
      },
      "bbox_norm": {
        "x1": 0.079167,
        "y1": 0.144444,
        "x2": 0.218229,
        "y2": 0.835185
      }
    },
    {
      "detection_id": "9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21:det-2",
      "object_type": "PERSON",
      "confidence": 0.88,
      "track_id": null,
      "bbox": {
        "x1": 816,
        "y1": 197,
        "x2": 1093,
        "y2": 834
      },
      "bbox_norm": {
        "x1": 0.425,
        "y1": 0.182407,
        "x2": 0.569271,
        "y2": 0.772222
      }
    }
  ],
  "zone_matches": [
    {
      "detection_id": "9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21:det-1",
      "zone_id": "danger_q2",
      "inside": true,
      "basis": "bbox_bottom_center",
      "overlap_ratio": 0.42
    },
    {
      "detection_id": "9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21:det-1",
      "zone_id": "forklift_lane",
      "inside": true,
      "basis": "bbox_bottom_center",
      "overlap_ratio": 0.31
    }
  ],
  "sensors": {
    "ultra_front": {
      "id": "ultra_front_01",
      "type": "ultrasonic",
      "ts": "2026-05-11T12:00:00.050Z",
      "status": "ALERT",
      "unit": "m",
      "value": 1.5,
      "zone_ids": ["danger_q2", "forklift_lane"]
    },
    "ultra_rear": {
      "id": "ultra_rear_01",
      "type": "ultrasonic",
      "ts": "2026-05-11T12:00:00.050Z",
      "status": "OK",
      "unit": "m",
      "value": 2.2,
      "zone_ids": ["rear_area"]
    }
  },
  "alerts": [
    {
      "alert_id": "alert-001",
      "event_type": "ZONE_INTRUSION",
      "event_status": "ACTIVE",
      "severity": "HIGH",
      "object_refs": ["9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21:det-1"],
      "sensor_refs": ["ultra_front"],
      "zone_refs": ["danger_q2", "forklift_lane"],
      "message": "작업자 1명 danger_q2, forklift_lane 진입 감지",
      "reason": {
        "code": "ZONE_INTRUSION",
        "factors": ["PERSON_DETECTED", "ZONE_INTRUSION", "ULTRA_FRONT_ALERT"]
      }
    }
  ]
}
```

## Backend Request

```http
POST /api/ai/events HTTP/1.1
Content-Type: application/json
```

The request body is one frame analysis JSON object.

- `analysis_id` identifies one analyzed frame payload.
- `detections[]` contains zero or more visual detections for that frame.
- `detections[].bbox` contains original-frame pixel coordinates.
- `detections[].bbox_norm` contains normalized 0.0-1.0 coordinates for frontend overlays.
- `zones[]` contains the zone definitions applied to this frame.
- `zone_matches[]` contains detection-to-zone rule results.
- `sensors` is a snapshot map keyed by sensor name.
- `sensors.*.zone_ids[]` is optional and maps sensors to one or more zones.
- `alerts[]` contains rule results and references detections/sensors/zones by ID.
- `alerts[].message` is display text. Search, stats, and storage logic should still use structured fields such as `event_type`, `severity`, refs, and `reason`.
- There is no top-level `sensor_status`. Each sensor has its own `status`.

The backend should return any `2xx` status for successful receipt. Non-`2xx` responses are treated as send failures and are spooled locally by the AI runtime.

## Timestamp Meaning

- `frame_ts`: when the video frame was captured/read.
- `ts`: when the AI frame analysis payload was created.
- `sensors.*.ts`: when each sensor reading was measured or last updated.

All timestamps use UTC ISO8601 strings.

## Sensor Status Values

- `OK`: sensor value is normal
- `WARN`: sensor requires attention
- `ALERT`: dangerous sensor value
- `CRITICAL`: immediate response needed
- `STALE`: latest reading is too old
- `OFFLINE`: sensor is unavailable
- `UNKNOWN`: status cannot be determined

## Current Rule Baseline

The current baseline rule engine is intentionally simple and should not be treated as a final industrial safety policy.

- Zone definitions are top-level `zones[]`, not detection fields.
- Detection-to-zone results are top-level `zone_matches[]`.
- Zone rules currently support quadrant-based zones in runtime, while the contract supports polygon-style `points_norm`.
- Zone intrusion currently checks whether the PERSON bounding-box center is inside a configured quadrant.
- Sensor threshold rules can raise alerts such as `PROXIMITY_RISK`.
- A final version should define polygon zones and a better position rule, such as bottom-center/foot point or polygon-overlap ratio.

## Legacy Note

The old shape used one `event_id` payload per detected object. That shape is deprecated for cross-team integration because frontend rendering and timestamp matching need all detections from the same frame together. Transitional code may still accept old `event_id` payloads, but new integrations should use one `analysis_id` payload with `zones[]`, `detections[]`, `zone_matches[]`, and `alerts[]`.
