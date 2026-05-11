# AI Runtime Team Contract

This is the current cross-team contract for `be-ai-endpoint` after the 2026-05-11 local E2E alignment.

## Common Rules

- Camera unit: one AI Runtime process owns exactly one camera.
- Output unit: one analyzed frame produces one JSON payload.
- Time format: all timestamps use UTC ISO8601 strings.
- Send failure: backend send failures must not stop the runtime. Failed payloads go to the local spool.
- Sensor status: do not use top-level `sensor_status`. Each sensor object owns its own `status`.
- Zone field: the official field is `detections[].zones[]`. The old singular `zone` field is a compatibility representative only.

## POST /api/ai/events Payload

Required top-level fields:

- `analysis_id`: UUID for one frame analysis payload
- `ts`: payload creation timestamp
- `site_id`: site/location ID
- `camera_id`: camera ID
- `frame_id`: frame number from this camera stream
- `frame_ts`: timestamp of the video frame
- `frame_width`: original frame width
- `frame_height`: original frame height
- `detections`: visual detections in this frame
- `sensors`: sensor snapshot map at decision time
- `alerts`: rule-engine decisions for this frame

## Field Cardinality

| Field | Cardinality | Contract |
|---|---:|---|
| `analysis_id` | 1 | ID for one frame analysis payload |
| `detections[]` | 0..N | Objects in the same frame; multiple people can be sent together |
| `detections[].bbox` | 1 | One bbox per detection |
| `detections[].bbox_norm` | 1 | Normalized 0.0-1.0 bbox for frontend overlays |
| `detections[].zones[]` | 0..N | Zones containing this detection; supports overlapping polygon/compound zones |
| `detections[].zone` | 0..1 | Legacy/compat representative zone. New consumers should use `zones[]` |
| `detections[].event_type` | 1 | Representative detection decision. Multiple situations should be expressed as multiple `alerts[]` entries |
| `sensors` | 0..N map | Snapshot keyed by sensor name |
| `sensors.*.zone_ids[]` | 0..N | Optional zones monitored by this sensor |
| `alerts[]` | 0..N | Situation decisions; backend alarm storage should use this |
| `alerts[].object_refs[]` | 0..N | Related `detection_id` values |
| `alerts[].sensor_refs[]` | 0..N | Related sensor keys |
| `alerts[].zone_refs[]` | 0..N | Related zone IDs |
| `alerts[].message` | 1 | Human-readable display text generated from structured alert fields |
| `reason.factors[]` | 0..N | Decision evidence factors |

## detections[]

Each detection is the basic unit for drawing a bbox.

- `detection_id`: unique detection ID, for example `{analysis_id}:det-1`
- `object_type`: `PERSON`, `HELMET`, `FORKLIFT`, `SENSOR`, etc.
- `confidence`: model confidence
- `track_id`: tracking ID; `null` when tracking is not active
- `bbox`: `{ x1, y1, x2, y2 }` in original frame coordinates
- `bbox_norm`: `{ x1, y1, x2, y2 }` normalized by `frame_width` and `frame_height`; use this for responsive frontend overlays
- `zones`: array of zone objects, for example `[{ zone_id, inside, zone_type }]`
- `zone`: compatibility representative zone. Backend/frontend should prefer `zones[]`
- `event_type`: representative detection decision, for example `DETECTION`, `ZONE_INTRUSION`, `PROXIMITY_RISK`
- `severity`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `reason`: `{ code, factors[] }`

## sensors

`sensors` is a map keyed by sensor name. `zone_ids` is optional and represents the video zones monitored by that sensor.

```json
{
  "ultra_front": {
    "id": "ultra_front_01",
    "type": "ultrasonic",
    "ts": "2026-05-11T12:00:00.050Z",
    "status": "ALERT",
    "unit": "m",
    "value": 1.5,
    "zone_ids": ["danger_q2", "forklift_lane"]
  }
}
```

Allowed sensor status values: `OK`, `WARN`, `ALERT`, `CRITICAL`, `STALE`, `OFFLINE`, `UNKNOWN`.

## alerts[]

`alerts[]` is the final situation-decision array for backend alarm storage and frontend warning display.

- `alert_id`: unique alert ID
- `event_type`: `ZONE_INTRUSION`, `PROXIMITY_RISK`, etc.
- `event_status`: `ACTIVE`, `ACKED`, `RESOLVED`, `FALSE_POSITIVE`
- `severity`: alert severity
- `object_refs`: related detection IDs
- `sensor_refs`: related sensor keys
- `zone_refs`: related zone IDs
- `message`: display text for frontend/admin screens
- `reason`: `{ code, factors[] }`

If multiple risk situations happen in one frame, create multiple `alerts[]` entries. Do not add an `event_type[]` array inside a detection.
Do not use `message` as the only stored source of truth. Backend search, statistics, filtering, and legal/evidence records should rely on `event_type`, `severity`, refs, and `reason`.

## Timestamp Contract

- `frame_ts`: video-frame timestamp. Frontend video/bbox alignment should use this.
- `ts`: AI payload creation timestamp.
- `sensors.*.ts`: sensor reading timestamp or latest update timestamp.

Frontend alignment should use `camera_id + frame_id + frame_ts`.

## Current Rule Baseline

The current rule engine is a baseline, not final industrial safety logic.

- Zone rules currently support quadrant settings.
- If one detection matches multiple configured zones, all matches are emitted in `zones[]`.
- Current zone intrusion uses the PERSON bbox center point.
- Sensor thresholds can raise alerts such as `PROXIMITY_RISK`.
- Sensor-only analysis can be emitted when there is sensor risk without visual detection.

Future improvements:

- Define real risk zones as polygons, not quadrants.
- Use bottom-center/foot point or polygon overlap ratio instead of bbox center.
- Verify that `alerts[].object_refs[]` points only to the actually risky objects when multiple people appear together.
- Map sensor direction/location to video zones so one sensor alert is not blindly attached to every detection.

## Team Responsibilities

### AI Runtime

- Read video frames
- Run model inference
- Reflect sensor snapshots
- Build frame analysis payloads
- Send `POST /api/ai/events`
- Spool unsent payloads on backend failure

AI Runtime does not own final DB schema, user notification policy, or frontend UI.

### Backend

Backend should provide:

- `POST /api/ai/events` endpoint
- Meaning of `2xx` and non-`2xx` responses
- Idempotency policy based on `analysis_id`
- Storage policy for frame analysis, detections, detection zones, alerts, and sensor snapshots

Recommended DB shape:

- `frame_analysis`: `analysis_id`, `site_id`, `camera_id`, `frame_id`, `frame_ts`, `ts`, frame size
- `detections`: `detection_id`, `analysis_id`, object/bbox/confidence
- `detection_zones`: `detection_id`, `zone_id`, inside, zone_type, or `detections.zones` JSONB
- `alerts`: `alert_id`, `analysis_id`, event_type/severity/status/reason, `zone_refs`
- `sensor_snapshots`: `analysis_id`, sensor key, sensor object

If the existing tables stay, unpack `detections[]` and `detections[].zones[]` into multiple rows or JSONB.

### Frontend

Frontend should consume:

- Latest frame analysis or frame analysis history
- Multiple bbox entries from `detections[]`
- Multiple zone labels/colors from `detections[].zones[]`
- Risk state from `alerts[]`
- Stale/disconnected state rules

Frontend should not command AI Runtime directly; it should read backend or event-bridge data.

### Streaming

Streaming should provide:

- Stable stream URL per `camera_id`
- Codec, fps, and resolution
- Stream healthcheck method
- Frame timestamp source, or a structure that lets AI read the same frame timeline

In operation, frontend and AI must not watch unrelated playback positions for the same camera.

### IoT

IoT should provide:

- Sensor name, ID, type, unit
- Measurement interval
- Stale/offline rule
- JSON payload examples
- Sensor location/direction to video-zone mapping
- `zone_ids[]` when one sensor monitors one or more zones

## Sign-off Checklist

- [ ] Backend: accepts `analysis_id + detections[] + detections[].zones[] + sensors + alerts[]`
- [ ] Backend: defines duplicate handling based on `analysis_id`
- [ ] Frontend: can draw multiple boxes from `detections[]`
- [ ] Frontend: can display multiple zones from `zones[]`
- [ ] Streaming: confirms `camera_id`, stream URL, fps, and resolution
- [ ] IoT: confirms sensor catalog, status values, and `zone_ids[]`
- [ ] AI: clearly shares that current zone/rule logic is baseline until final policy is decided
