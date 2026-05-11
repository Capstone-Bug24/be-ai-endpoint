# AI Runtime 공통 계약 문서

이 디렉터리는 AI Runtime과 다른 팀이 함께 맞춰야 하는 API 계약, 책임 경계, 용어를 정리한다. 독자는 Backend, Frontend, Streaming, IoT, AI 담당자다.

## 현재 기준

AI Runtime의 공식 출력은 `POST /api/ai/events`로 보내는 frame analysis payload다.

```text
1 analyzed frame = 1 JSON payload
payload = analysis_id + zones[] + detections[] + sensors + alerts[]
```

기존 `event_id` 단건 이벤트 방식은 legacy 호환용으로만 본다. 새 연동은 `analysis_id` 기준의 프레임 단위 payload를 사용한다.

## 검증 범위

이 문서는 현재 `be-ai-endpoint` 코드와 shared 문서 기준으로 정리한 AI Runtime 출력 계약이다. 문서가 직접 확정하는 범위는 AI Runtime이 backend로 보내는 payload 구조, 좌표 기준, 팀별 책임 경계다.

Backend 저장 구현, Frontend 표시 구현, Streaming의 실제 stream URL/fps/resolution, IoT sensor catalog는 각 담당 팀의 확인이 필요하다. 이 항목들은 [team_contract.md](team_contract.md)의 sign-off checklist에서 추적한다.

## 읽는 순서

1. [architecture.md](architecture.md): 시스템 경계와 데이터 흐름
2. [team_contract.md](team_contract.md): 팀별 책임과 API 계약
3. [schema_examples.md](schema_examples.md): 실제 JSON 예시
4. [glossary.md](glossary.md): 용어 정리

## 책임 매트릭스

| 팀 | 책임 범위 | AI에 제공해야 하는 것 | AI에서 받는 것 | AI 책임이 아닌 것 |
|---|---|---|---|---|
| AI/Runtime | 프레임 입력, 모델 추론, 센서 snapshot 반영, baseline rule, frame analysis payload 생성, backend 전송, spool fallback | 없음 | schema feedback, backend response contract, stream/sensor contract | 최종 DB schema, 사용자 알림 정책, frontend UI |
| Streaming | 카메라 stream 운영 | `camera_id`, stream URL, codec, fps, resolution, healthcheck | AI가 소비하는 `camera_id` 정보 | 모델 추론, 이벤트 schema, backend 저장 |
| IoT | 센서 하드웨어와 sensor payload | 센서 이름, ID, type, unit, 측정 주기, stale/offline rule, JSON 예시, sensor-to-zone mapping | `sensors`에 반영되는 sensor snapshot | 모델 추론, alert 생성, backend 저장 |
| Backend | frame analysis 수신과 저장, 정책, 최종 알림 | `POST /api/ai/events`, 응답 의미, idempotency, 저장 계약 | 분석된 프레임 1개당 JSON 1개 | 모델 추론, stream 운영, 센서 하드웨어 |
| Frontend | dashboard와 운영 UI 표시 | stale 표시 규칙, bbox/alert 표시 요구사항 | backend 또는 event bridge가 제공하는 frame analysis 데이터 | stream 운영, 이벤트 생성, 최종 backend 정책 |

## 반드시 맞춰야 할 기준

- Frontend는 `detections[]`의 여러 bbox를 동시에 그릴 수 있어야 한다.
- Frontend는 반응형 overlay 표시에는 `bbox_norm`을 우선 사용하고, 원본 기록과 디버깅에는 `bbox`를 함께 사용할 수 있다.
- Backend는 `analysis_id`를 최상위 idempotency key로 취급해야 한다.
- `alerts[].object_refs`는 raw bbox가 아니라 `detection_id`를 참조한다.
- 센서 상태는 최상위 `sensor_status`로 보내지 않는다. 각 sensor object가 자기 `status`를 가진다.
- `frame_ts`는 영상 source 기준 timestamp이고, `frame_ts_source`는 그 값의 출처다.
- `ts`는 payload 생성 timestamp다.
- `zones[]`는 `points`와 `points_norm`을 가진 위험구역 정의다. alert별 zone 판정 근거는 필요할 때 `alerts[].evidence[]`에 둔다.
