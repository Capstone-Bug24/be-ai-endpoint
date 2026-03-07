# AI Runtime 공유 예시

이 문서는 계약을 설명하기 위한 예시 모음이다. 필드 이름과 기본 타입은 현재 시스템 기준을 따르지만, 값 자체는 예시일 수 있다.

## 계약과 예시의 구분

- `event_id`, `ts`, `camera_id` 같은 키 이름과 기본 타입은 계약이다.
- 아래 JSON 값, RTSP URL, 센서 이름은 이해를 돕기 위한 예시다.
- 백엔드 응답 바디는 참고용 예시이며, 런타임 계약의 핵심은 상태코드가 `2xx`인지 `non-2xx`인지다.

## 이벤트 JSON 예시

```json
{
  "event_id": "9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21",
  "ts": "2026-03-08T01:23:45.123456+00:00",
  "site_id": "S001",
  "camera_id": "cam01",
  "event_type": "ZONE_INTRUSION",
  "object_type": "PERSON",
  "severity": "LOW",
  "track_id": 42,
  "confidence": 0.75,
  "bbox": {
    "x1": 120,
    "y1": 48,
    "x2": 204,
    "y2": 176
  },
  "zone": {
    "zone_id": "",
    "inside": false
  },
  "sensors": {
    "ultra_front": {
      "sensor": "ultra_front",
      "ts": "2026-03-08T01:23:44.900000+00:00",
      "data": {
        "distance_m": 1.2,
        "status": "ok"
      }
    },
    "ultra_rear": {
      "sensor": "ultra_rear",
      "ts": "2026-03-08T01:23:44.850000+00:00",
      "data": {
        "distance_m": 1.7,
        "status": "ok"
      }
    }
  }
}
```

현재 시스템 기준으로 `zone.zone_id`는 빈 문자열일 수 있고, `zone.inside`는 `false`일 수 있다.

## 백엔드 요청/응답 예시

### 요청 예시

```http
POST /api/events HTTP/1.1
Content-Type: application/json

{
  "event_id": "9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21",
  "ts": "2026-03-08T01:23:45.123456+00:00",
  "site_id": "S001",
  "camera_id": "cam01",
  "event_type": "ZONE_INTRUSION",
  "object_type": "PERSON",
  "severity": "LOW",
  "track_id": 42,
  "confidence": 0.75,
  "bbox": {
    "x1": 120,
    "y1": 48,
    "x2": 204,
    "y2": 176
  },
  "zone": {
    "zone_id": "",
    "inside": false
  },
  "sensors": {}
}
```

### 성공 응답 예시 (`2xx`)

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "status": "accepted",
  "event_id": "9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21"
}
```

### 실패 응답 예시 (`non-2xx`)

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "status": "retry_later"
}
```

## RTSP 레지스트리 예시

| camera_id | rtsp_url | codec | fps | resolution | owner | healthcheck |
|---|---|---|---:|---|---|---|
| `cam01` | `rtsp://stream-host:8554/cam1` | `H264` | 10 | `1280x720` | Streaming team | `ffprobe rtsp://stream-host:8554/cam1` |
| `cam02` | `rtsp://stream-host:8554/cam2` | `H264` | 10 | `1280x720` | Streaming team | `ffprobe rtsp://stream-host:8554/cam2` |

## IoT 센서 카탈로그 예시

| name | type | unit | interval_sec | stale_timeout_sec | sample_payload |
|---|---|---|---:|---:|---|
| `ultra_front` | `ultrasonic` | `m` | 0.2 | 1.0 | `{"distance_m": 1.2, "status": "ok"}` |
| `ultra_rear` | `ultrasonic` | `m` | 0.4 | 1.0 | `{"distance_m": 1.7, "status": "ok"}` |

## 센서 payload 예시

### 초음파 센서 예시

```json
{
  "distance_m": 1.2,
  "status": "ok"
}
```

### 온도 센서 예시

```json
{
  "temperature_c": 27.4,
  "status": "ok"
}
```
