# AI Runtime 팀 계약

이 문서는 `be-ai-endpoint`가 다른 팀과 맞춰야 하는 frame analysis 계약을 정의한다. 기준 시점은 2026-05-11 로컬 E2E 정렬 이후다.

## 문서 범위

이 문서는 AI Runtime의 출력 payload와 팀 간 연동 책임을 정의한다. 현재 파일 기준으로 확인한 구현 사실과, 팀별 확인이 필요한 항목을 분리해서 적는다.

- 확인한 범위: AI Runtime의 frame analysis payload 구조, `detections[]`/`zones[]`/`sensors`/`alerts[]` 역할 분리, 좌표 표기 기준.
- 확인이 필요한 범위: Backend의 최종 DB schema와 idempotency 정책, Frontend overlay 구현, Streaming timestamp source, IoT sensor catalog와 sensor-to-zone mapping.

## 공통 규칙

- 카메라 단위: AI Runtime 프로세스 1개는 카메라 1대를 담당한다.
- 출력 단위: 분석된 프레임 1개는 JSON payload 1개로 전송한다.
- 시간 형식: 모든 timestamp는 UTC ISO8601 문자열을 사용한다.
- 전송 실패: backend 전송 실패는 runtime을 중단하지 않는다. 실패한 payload는 local spool에 저장한다.
- 센서 상태: 최상위 `sensor_status`는 사용하지 않는다. 각 sensor object가 자기 `status`를 가진다.
- Zone 필드: zone 정의는 최상위 `zones[]`에 둔다. detection-to-zone 판정 근거는 필요할 때 `alerts[].evidence[]`에 둔다.

## `POST /api/ai/events` Payload

필수 최상위 필드는 다음과 같다.

- `analysis_id`: 프레임 분석 payload 1건의 UUID
- `ts`: AI Runtime이 payload를 생성한 시각
- `site_id`: 현장 또는 설치 위치 ID
- `camera_id`: 카메라 ID
- `frame_id`: 해당 카메라 stream에서 읽은 프레임 번호
- `frame_ts`: 영상 source 기준 timestamp
- `frame_ts_source`: `frame_ts` 값의 출처
- `frame_width`: 원본 프레임 너비
- `frame_height`: 원본 프레임 높이
- `zones`: 해당 프레임에 적용된 zone 정의
- `detections`: 해당 프레임의 시각 객체 탐지 결과
- `sensors`: 판단 시점의 sensor snapshot map
- `alerts`: rule engine이 만든 상황 판단 결과

## 필드 수량

| 필드 | 수량 | 계약 |
|---|---:|---|
| `analysis_id` | 1 | 프레임 분석 payload 1건의 ID |
| `frame_ts` | 1 | 영상 source 기준 timestamp. source timestamp가 없으면 fallback timestamp를 사용한다. |
| `frame_ts_source` | 1 | `stream`, `ai_read_time`, `provided`, `ai_payload_time` 중 하나 |
| `detections[]` | 0..N | 같은 프레임의 객체 목록. 여러 사람을 한 번에 보낼 수 있다. |
| `detections[].bbox` | 1 | detection 1개의 원본 프레임 기준 bbox |
| `detections[].bbox_norm` | 1 | frontend overlay용 0.0~1.0 정규화 bbox |
| `zones[]` | 0..N | 이 카메라/프레임에 적용된 zone 정의 |
| `zones[].points` | 0..N | 원본 프레임 기준 polygon pixel 좌표 |
| `zones[].points_norm` | 0..N | 0.0~1.0 정규화 polygon 좌표 |
| `sensors` | 0..N map | sensor 이름을 key로 사용하는 snapshot map |
| `sensors.*.zone_ids[]` | 0..N | 해당 sensor가 감시하는 zone ID 목록 |
| `alerts[]` | 0..N | 위험 상황 판단 결과. backend 알람 저장 기준이다. |
| `alerts[].object_refs[]` | 0..N | 관련 `detection_id` 목록 |
| `alerts[].sensor_refs[]` | 0..N | 관련 sensor key 목록 |
| `alerts[].zone_refs[]` | 0..N | 관련 zone ID 목록 |
| `alerts[].message` | 1 | 화면 표시용 문장 |
| `alerts[].evidence[]` | 0..N | detection-to-zone 판정, 센서 임계값 등 선택적 근거 |
| `reason.factors[]` | 0..N | 판단에 사용한 구조화된 근거 목록 |

## `detections[]`

`detections[]`는 bbox를 그리기 위한 모델 탐지 결과다. 위험 판단이나 알람 저장의 기준은 `detections[]`가 아니라 `alerts[]`다.

- `detection_id`: detection 1개의 ID. 예: `{analysis_id}:det-1`
- `object_type`: `PERSON`, `HELMET`, `FORKLIFT`, `SENSOR` 등
- `confidence`: 모델 confidence
- `track_id`: tracking ID. YOLO tracking이 켜진 경우 ByteTrack 등 tracker가 부여하며, tracking이 없으면 `null`
- `model_label`: 모델 원본 class label. 예: `Hardhat`, `NO-Safety Vest`
- `bbox`: `{ x1, y1, x2, y2 }` 형식의 원본 프레임 기준 좌표
- `bbox_norm`: `frame_width`, `frame_height`로 정규화한 `{ x1, y1, x2, y2 }`

Detection object는 모델 출력에 가깝게 유지한다. Zone/rule 판단 결과는 detection 안에 넣지 않고 `alerts[]`에 둔다.

## `zones[]`

`zones[]`는 해당 프레임에 적용된 위험구역 정의다. 현재 프로젝트는 frontend/backend가 별도 zone catalog 요청 없이 같은 기준을 볼 수 있도록 zone 정의를 frame payload에 포함한다.

- `zone_id`: 안정적으로 유지되는 zone ID
- `name`: 사람이 읽는 zone 이름. 선택 필드다.
- `zone_type`: `polygon`, `quadrant` 등
- `severity`: 이 zone의 기본 위험도
- `points`: 원본 프레임 기준 polygon pixel 좌표
- `points_norm`: 0.0~1.0 범위의 정규화 polygon 좌표

좌표 표기 순서는 detection과 맞춘다. 원본 pixel 좌표를 먼저 두고, 정규화 좌표를 뒤에 둔다. Polygon 점은 외곽선을 따라 순서대로 나열하며, 첫 점을 마지막에 반복하지 않는다.

## `sensors`

`sensors`는 sensor 이름을 key로 사용하는 snapshot map이다. `zone_ids`는 선택 필드이며, 해당 sensor가 감시하는 영상 zone을 나타낸다.

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

허용하는 sensor status 값은 `OK`, `WARN`, `ALERT`, `CRITICAL`, `STALE`, `OFFLINE`, `UNKNOWN`이다.

## `alerts[]`

`alerts[]`는 backend 알람 저장과 frontend 경고 표시의 기준이 되는 최종 상황 판단 배열이다.

- `alert_id`: alert 1개의 ID
- `event_type`: `ZONE_INTRUSION`, `PROXIMITY_RISK` 등
- `event_status`: `ACTIVE`, `ACKED`, `RESOLVED`, `FALSE_POSITIVE`
- `severity`: alert 위험도
- `object_refs`: 관련 `detection_id` 목록
- `sensor_refs`: 관련 sensor key 목록
- `zone_refs`: 관련 zone ID 목록
- `message`: frontend/admin 화면 표시용 문장
- `evidence`: 선택적 machine-readable 근거. 예: `{ type, detection_id, zone_id, inside, basis, overlap_ratio }`
- `reason`: `{ code, factors[] }`

한 프레임에서 여러 위험 상황이 발생하면 `alerts[]`에 여러 entry를 만든다. Detection 안에 `event_type[]` 배열을 넣지 않는다.

`message`는 화면 표시용이다. 검색, 통계, 저장, 법적 근거 기록은 `event_type`, `severity`, refs, `reason` 같은 구조화 필드를 우선 사용한다.

## Timestamp 계약

- `frame_ts`: 영상 source 기준 timestamp. Streaming이 frame timestamp 또는 PTS를 제공하면 AI Runtime은 그 값을 사용한다.
- `frame_ts_source`: `frame_ts`의 출처. 현재 fallback 값은 `ai_read_time`이다.
- `ts`: AI Runtime이 payload를 생성한 timestamp.
- `sensors.*.ts`: sensor reading이 측정되었거나 마지막으로 갱신된 timestamp.

Frontend의 정렬 기준은 `camera_id + frame_id + frame_ts`다.
Streaming이 source timestamp를 제공하지 않는 local file, webcam, mock 환경에서는 AI Runtime이 frame을 읽은 시각을 `frame_ts` fallback으로 사용한다. 이 fallback은 테스트에는 사용할 수 있지만, 실제 운영에서 frontend 영상과 AI bbox를 정확히 동기화하는 기준으로 보기는 어렵다.

## 좌표 계약

- 원점: 원본 프레임의 왼쪽 위.
- Pixel 좌표 기준: `frame_width`, `frame_height`.
- 정규화 좌표 기준: `x / frame_width`, `y / frame_height`.
- Bbox 형식: `bbox`와 `bbox_norm`은 `xyxy` 형식을 사용한다.
- Zone 형식: `points`와 `points_norm`은 순서가 있는 polygon 점 배열을 사용한다.
- Frontend는 반응형 overlay 표시에는 정규화 좌표를 우선 사용하고, 원본 기록과 디버깅에는 pixel 좌표를 함께 사용할 수 있다.

## 현재 rule 기준

현재 rule engine은 영상 detection, polygon zone, sensor snapshot을 하나의 frame analysis로 묶는 판단 계층이다.

- Runtime의 zone rule은 polygon과 quadrant 설정을 지원한다.
- Detection 1개가 여러 zone과 매칭되어 alert를 만들면, 해당 alert는 여러 `zone_refs[]`와 선택적 `evidence[]`를 가질 수 있다.
- 현재 zone intrusion 판정은 PERSON bbox의 하단 영역(`bbox_bottom_band`)이 zone polygon 안에 들어오는 비율을 기준으로 한다.
- Sensor threshold rule은 `PROXIMITY_RISK` 같은 alert를 만들 수 있다.
- 시각 detection이 없어도 sensor 위험만으로 sensor-only analysis를 보낼 수 있다.

운영 설정에서는 실제 위험구역을 camera별 polygon으로 정의해야 한다. 여러 사람이 동시에 나올 때는 `alerts[].object_refs[]`가 실제 위험 객체만 참조해야 하며, sensor 방향과 위치는 `sensors.*.zone_ids[]`로 영상 zone에 매핑한다.

## 팀별 책임

### AI Runtime

- 영상 frame 읽기
- 모델 추론 실행
- sensor snapshot 반영
- frame analysis payload 생성
- `POST /api/ai/events` 전송
- 전송 실패 payload spool 저장

AI Runtime은 최종 DB schema, 사용자 알림 정책, frontend UI를 책임지지 않는다.

### Backend

Backend는 다음 항목을 제공해야 한다.

- `POST /api/ai/events` endpoint
- `2xx`와 non-`2xx` 응답의 의미
- `analysis_id` 기준 idempotency 정책
- frame analysis, detections, zones, alerts, sensor snapshots 저장 정책

권장 DB 형태는 다음과 같다.

- `frame_analysis`: `analysis_id`, `site_id`, `camera_id`, `frame_id`, `frame_ts`, `ts`, frame size
- `detections`: `detection_id`, `analysis_id`, object/bbox/confidence
- `zones`: `analysis_id`, `zone_id`, zone_type, points/points_norm, severity 또는 raw `zones` JSONB
- `alerts`: `alert_id`, `analysis_id`, event_type/severity/status/reason, `zone_refs`
- `sensor_snapshots`: `analysis_id`, sensor key, sensor object

기존 table을 유지한다면 raw payload JSONB를 먼저 저장하고, 필요한 경우 `alerts[]`만 flatten하는 방식을 권장한다.

### Frontend

Frontend는 다음 데이터를 소비한다.

- 최신 frame analysis 또는 frame analysis history
- `detections[]`의 여러 bbox
- 최상위 `zones[]`의 zone polygon
- `alerts[]`의 위험 상태
- stale/disconnected 표시 규칙

Frontend는 AI Runtime을 직접 제어하지 않는다. Backend 또는 event bridge가 제공하는 데이터를 읽는다.

### Streaming

Streaming은 다음 항목을 제공해야 한다.

- `camera_id`별 안정적인 stream URL
- codec, fps, resolution
- stream healthcheck 방법
- frame timestamp source, PTS, frame sequence 중 하나
- AI와 Frontend가 같은 frame timeline을 읽을 수 있는 구조

운영 환경에서 frontend와 AI가 같은 카메라의 서로 다른 playback 위치를 보고 있으면 안 된다.
Frontend가 stream을 `iframe`으로 표시하는 경우, iframe 자체를 frame timestamp source로 취급하지 않는다. Cross-origin iframe이나 단순 player page는 원본 frame PTS를 안정적으로 노출하지 않기 때문이다. Streaming은 별도 metadata API/WebSocket, player event, HLS `PROGRAM-DATE-TIME`, WebRTC/RTP timestamp mapping 등 명시적인 동기화 기준을 제공해야 한다.

### IoT

IoT는 다음 항목을 제공해야 한다.

- Sensor name, ID, type, unit
- 측정 주기
- stale/offline rule
- JSON payload 예시
- Sensor 위치/방향과 video-zone mapping
- Sensor 1개가 zone 1개 이상을 감시할 때의 `zone_ids[]`

## Sign-off checklist

- [ ] Backend: `zones[] + detections[] + sensors + alerts[]`를 가진 payload 1개를 수신한다.
- [ ] Backend: `analysis_id` 기준 중복 처리 정책을 정의한다.
- [ ] Frontend: `detections[]`의 여러 bbox를 그릴 수 있다.
- [ ] Frontend: `zones[]`의 여러 polygon을 표시할 수 있다.
- [ ] Streaming: `camera_id`, stream URL, fps, resolution, frame timestamp source를 확정한다.
- [ ] IoT: sensor catalog, status 값, `zone_ids[]`를 확정한다.
- [ ] AI: ByteTrack 등 tracking 사용 여부와 zone 판정 기준(`bbox_bottom_band`)을 공유한다.
