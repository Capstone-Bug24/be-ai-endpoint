# AI Runtime 공통 Schema 예시

이 문서는 `be-ai-endpoint`가 backend로 보내는 frame analysis JSON 예시를 제공한다. 현재 계약은 프레임 단위다. 분석된 프레임 1개는 JSON payload 1개로 전송한다.

## Frame Analysis JSON

```json
{
  "analysis_id": "9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21",
  "ts": "2026-05-11T12:00:00.120Z",
  "site_id": "S001",
  "camera_id": "cam01",
  "frame_id": 318,
  "frame_ts": "2026-05-11T12:00:00.000Z",
  "frame_ts_source": "stream",
  "frame_width": 1920,
  "frame_height": 1080,
  "zones": [
    {
      "zone_id": "danger_q2",
      "name": "위험구역 2",
      "zone_type": "polygon",
      "severity": "HIGH",
      "points": [
        { "x": 0, "y": 0 },
        { "x": 960, "y": 0 },
        { "x": 960, "y": 540 },
        { "x": 0, "y": 540 }
      ],
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
      "points": [
        { "x": 230, "y": 216 },
        { "x": 922, "y": 194 },
        { "x": 1056, "y": 778 },
        { "x": 192, "y": 821 }
      ],
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
      "evidence": [
        {
          "type": "zone_match",
          "detection_id": "9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21:det-1",
          "zone_id": "danger_q2",
          "inside": true,
          "basis": "bbox_bottom_center",
          "overlap_ratio": 0.42
        },
        {
          "type": "zone_match",
          "detection_id": "9df4d017-73a8-4b1b-b9e9-a1bc2c7f6d21:det-1",
          "zone_id": "forklift_lane",
          "inside": true,
          "basis": "bbox_bottom_center",
          "overlap_ratio": 0.31
        }
      ],
      "reason": {
        "code": "ZONE_INTRUSION",
        "factors": ["PERSON_DETECTED", "ZONE_INTRUSION", "ULTRA_FRONT_ALERT"]
      }
    }
  ]
}
```

## Backend 요청

```http
POST /api/ai/events HTTP/1.1
Content-Type: application/json
```

요청 body는 frame analysis JSON object 1개다.

- `analysis_id`는 분석된 프레임 payload 1건을 구분한다.
- `detections[]`는 같은 프레임에서 탐지한 객체 목록이다.
- `detections[].bbox`는 원본 프레임 기준 pixel 좌표다.
- `detections[].bbox_norm`은 0.0~1.0 범위의 정규화 좌표다. Frontend overlay 표시에는 이 값을 우선 사용한다.
- `zones[]`는 해당 프레임에 적용된 zone 정의다.
- `zones[].points`는 원본 프레임 기준 polygon pixel 좌표다.
- `zones[].points_norm`은 0.0~1.0 범위의 정규화 polygon 좌표다.
- `sensors`는 sensor 이름을 key로 사용하는 snapshot map이다.
- `sensors.*.zone_ids[]`는 sensor가 감시하는 zone ID 목록이다. 선택 필드다.
- `alerts[]`는 rule 결과이며, `detections[]`, `sensors`, `zones[]`를 ID로 참조한다.
- `alerts[].message`는 화면 표시용 문장이다. 검색, 통계, 저장 로직은 `event_type`, `severity`, refs, `reason` 같은 구조화 필드를 우선 사용해야 한다.
- `alerts[].evidence[]`는 선택적 machine-readable 판단 근거다.
- 최상위 `sensor_status`는 사용하지 않는다. 각 sensor object가 자기 `status`를 가진다.

Backend는 정상 수신 시 `2xx` status를 반환해야 한다. Non-`2xx` 응답은 전송 실패로 간주하며, AI Runtime은 해당 payload를 local spool에 저장한다.

## Timestamp 의미

- `frame_ts`: 영상 source 기준 timestamp. Streaming이 frame timestamp 또는 PTS를 제공하면 그 값을 사용한다.
- `frame_ts_source`: `frame_ts` 값의 출처. 예: `stream`, `ai_read_time`, `provided`, `ai_payload_time`.
- `ts`: AI Runtime이 frame analysis payload를 생성한 시각.
- `sensors.*.ts`: 각 sensor reading이 측정되었거나 마지막으로 갱신된 시각.

모든 timestamp는 UTC ISO8601 문자열을 사용한다.
Streaming timestamp가 없는 local file, webcam, mock 환경에서는 AI Runtime이 frame을 읽은 시각을 `ai_read_time` fallback으로 사용한다.

## Sensor Status 값

- `OK`: sensor 값이 정상 범위다.
- `WARN`: sensor 확인이 필요하다.
- `ALERT`: sensor 값이 위험 기준에 걸렸다.
- `CRITICAL`: 즉시 대응이 필요한 상태다.
- `STALE`: 최신 reading이 기준 주기보다 오래되었다.
- `OFFLINE`: sensor를 사용할 수 없다.
- `UNKNOWN`: 상태를 판단할 수 없다.

## 현재 rule baseline

현재 baseline rule engine은 최종 산업안전 정책이 아니다. 통합 테스트와 역할 분리를 위한 최소 판단 로직이다.

- Zone 정의는 최상위 `zones[]`에 둔다. Detection object 안에 넣지 않는다.
- Detection-to-zone 판정 근거는 필요할 때 `alerts[].evidence[]`에 둔다.
- Runtime의 zone rule은 현재 quadrant 기반 설정을 지원하지만, 계약은 polygon 형태의 `points`와 `points_norm`을 지원한다.
- 현재 zone intrusion은 PERSON bbox center가 설정된 quadrant 안에 있는지 확인한다.
- Sensor threshold rule은 `PROXIMITY_RISK` 같은 alert를 만들 수 있다.
- 최종 버전에서는 실제 polygon zone, bottom-center/foot point, polygon overlap ratio 같은 더 나은 위치 판정 기준을 정의해야 한다.

## Legacy 참고

이전 구조는 detected object 1개당 `event_id` payload 1개를 보내는 방식이었다. 이 방식은 frontend rendering과 timestamp 정합성에 불리하므로 새 연동에는 사용하지 않는다.

전환기 호환 코드는 old `event_id` payload를 받을 수 있지만, 새 연동은 `analysis_id`를 가진 frame analysis payload를 사용한다.
