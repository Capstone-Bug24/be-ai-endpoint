# AI Runtime Shared Docs

이 디렉터리는 AI Runtime과 다른 팀이 맞춰야 하는 공통 계약 문서 모음이다.

## 현재 기준

현재 공식 출력 계약은 `POST /api/ai/events`로 보내는 frame analysis payload다.

```text
1 analyzed frame = 1 JSON payload
payload = analysis_id + zones[] + detections[] + sensors + alerts[]
```

기존 `event_id` 단건 이벤트 방식은 legacy 호환용으로만 본다.

## 읽는 순서

1. [architecture.md](architecture.md): 시스템 경계와 데이터 흐름
2. [team_contract.md](team_contract.md): 팀별 책임과 API 계약
3. [schema_examples.md](schema_examples.md): 실제 JSON 예시
4. [glossary.md](glossary.md): 용어 정리

## 책임 매트릭스

| Team | Owns | Must Provide To AI | Receives From AI | Out Of Scope For AI |
|---|---|---|---|---|
| AI/Runtime | frame ingest, inference, sensor fusion, rule baseline, frame analysis payload, backend send, spool fallback | none | schema feedback, backend response contract, stream/sensor contracts | final DB schema, final user notification policy, frontend UI ownership |
| Streaming | camera stream operation | `camera_id`, stream URL, codec, fps, resolution, healthcheck | which `camera_id` AI consumes | model inference, event schema, backend storage |
| IoT | sensor hardware and payload | sensor names, IDs, type, unit, interval, stale/offline rules, JSON examples, sensor-to-zone mapping | sensor snapshot reflected in `sensors` | inference, alerts, backend storage |
| Backend | receive/store frame analysis, policy, final alert delivery | `POST /api/ai/events`, response semantics, idempotency, storage contract | one frame analysis JSON per analyzed frame | model inference, stream operation, sensor hardware |
| Frontend | render dashboard and operation UI | stale display rules, bbox/alert display needs | backend/event-bridge data based on frame analysis schema | stream operation, event generation, final backend policy |

## Important Alignment Points

- Frontend must render multiple boxes from `detections[]`.
- Frontend should prefer `bbox_norm` for responsive overlays and keep `bbox` for original-frame debugging/records.
- Backend should treat `analysis_id` as the top-level idempotency key.
- `alerts[].object_refs` points to detection IDs, not raw bbox objects.
- Sensor status stays inside each sensor object.
- `frame_ts` is the video-frame timestamp; `ts` is payload creation time.
- `zones[]` defines polygons/quadrants for the frame; alert-specific zone evidence stays inside `alerts[].evidence[]`.
