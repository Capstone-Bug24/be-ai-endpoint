# AI Runtime Glossary

처음 보는 팀원이 용어를 빠르게 맞출 수 있도록 정리한 문서다.

| Term | Meaning |
|---|---|
| `analysis_id` | 프레임 분석 결과 1건을 구분하는 UUID. 현재 API payload의 최상위 ID다. |
| `detection_id` | `detections[]` 내부 객체 1개를 구분하는 ID. 프론트 bbox key와 alert 참조에 사용한다. |
| `alert_id` | `alerts[]` 내부 상황 판단 결과 1개를 구분하는 ID. |
| `camera_id` | 카메라를 구분하는 ID. Streaming, AI, Backend, Frontend가 같은 값을 사용해야 한다. |
| `site_id` | 현장 또는 설치 위치를 구분하는 ID. |
| `frame_id` | 특정 카메라에서 읽은 프레임 번호. 영상과 AI 결과를 맞추는 기준 중 하나다. |
| `frame_ts` | 해당 프레임이 수집/읽힌 시각. 영상과 bbox 정합성을 맞추는 핵심 timestamp다. |
| `ts` | AI가 frame analysis payload를 생성한 시각. |
| `bbox` | bounding box. `{x1, y1, x2, y2}` 원본 프레임 좌표를 사용한다. |
| `bbox_norm` | `bbox`를 `frame_width`, `frame_height`로 나눈 0.0~1.0 비율 좌표. 프론트 overlay 표시용이다. |
| `detection` | 한 프레임에서 모델이 찾은 객체 1개. 예: PERSON 1명. |
| `detections[]` | 같은 프레임에서 찾은 detection들의 배열. 여러 명을 한 번에 보낼 수 있다. |
| `zones[]` | frame payload에 포함되는 위험구역 정의 배열. polygon/quadrant 좌표와 zone ID를 담는다. |
| `alerts[].evidence[]` | alert가 왜 발생했는지에 대한 선택적 근거 배열. detection-zone 관계, 센서 조건 등을 담을 수 있다. |
| `sensor payload` | IoT 쪽이 제공하는 원본 센서 데이터 객체. |
| `sensor snapshot` | frame analysis 생성 시점에 AI Runtime이 들고 있는 최신 센서 상태 묶음. |
| `sensors` | frame analysis payload의 센서 snapshot map. key는 센서 이름이다. |
| `alert` | detection과 sensor snapshot을 rule로 판단한 결과. 백엔드 알람 저장과 프론트 경고 표시의 기준이다. |
| `object_refs` | alert가 참조하는 `detection_id` 배열. |
| `sensor_refs` | alert가 참조하는 sensor key 배열. |
| `zone_refs` | alert가 참조하는 zone ID 배열. |
| `message` | alert를 화면에 표시하기 위한 자연어 문장. 저장/통계/검색 기준은 구조화 필드를 우선 사용한다. |
| `spool` | 백엔드 전송 실패 시 payload를 로컬 JSONL 파일에 임시 저장하는 fallback. |
| `dry_run` | 백엔드 전송 없이 로컬 출력만 확인하는 실행 모드. |
| `stale` | 센서 데이터가 기준 주기보다 오래 갱신되지 않은 상태. |
| `RTSP reconnect` | RTSP stream이 끊겼을 때 같은 URL로 다시 붙는 복구 동작. |
| `event_id` | 이전 단건 이벤트 payload의 ID. 새 계약에서는 deprecated이며, 필요한 경우 legacy 호환용으로만 사용한다. |

## 헷갈리기 쉬운 구분

- `analysis_id`는 프레임 분석 payload 1건의 ID다.
- `detection_id`는 화면에 그릴 객체 1개의 ID다.
- `zones[]`는 zone 정의이고, detection-zone 판정 근거가 필요하면 `alerts[].evidence[]` 안에 넣는다.
- `alert_id`는 위험 상황 판단 결과 1개의 ID다.
- `frame_ts`는 영상 프레임 기준 시각이고, `ts`는 AI payload 생성 시각이다.
- AI Runtime은 `alerts[]`까지 만들지만, 최종 알림 전파/저장 정책은 Backend 책임이다.

## 같이 보면 좋은 문서

- 시스템 경계: [architecture.md](architecture.md)
- 팀 계약: [team_contract.md](team_contract.md)
- JSON 예시: [schema_examples.md](schema_examples.md)
