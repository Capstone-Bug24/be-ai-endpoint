# AI Runtime 용어집

이 문서는 처음 보는 팀원을 위한 최소 용어 설명이다.

| 용어 | 의미 |
|---|---|
| `camera_id` | 카메라를 식별하는 고유 키. AI Runtime 프로세스와 스트림 매핑의 기준이 된다. |
| `site_id` | 카메라가 속한 사이트 또는 설치 위치를 나타내는 식별자. |
| `event_id` | 이벤트 1건을 구분하는 고유 ID. 중복 저장 방지와 화면 키에 사용한다. |
| `sensor payload` | IoT 팀이 보내는 원본 센서 데이터 객체. 문자열이 아니라 JSON 객체여야 한다. |
| `sensor snapshot` | 이벤트 생성 시점에 AI Runtime이 붙여 넣는 최신 센서 상태 묶음. 각 센서는 `sensor`, `ts`, `data`를 가진다. |
| `spool` | 백엔드 전송이 실패했을 때 이벤트를 로컬 파일에 임시 적재해 두는 fallback 방식. |
| `dry_run` | 백엔드 전송 없이 런타임 동작과 JSON 출력만 확인하는 실행 모드. |
| `stale` | 센서나 데이터가 기대 주기보다 오래 갱신되지 않아 최신 상태라고 보기 어려운 상태. |
| `RTSP reconnect` | RTSP 스트림이 일시적으로 끊겼을 때 같은 URL로 다시 붙는 복구 동작. |
| `event` | AI Runtime이 생성하는 감지 기록. 백엔드 정책 처리 전의 원본 단위다. |
| `alert` | 백엔드가 이벤트를 바탕으로 정책을 적용한 뒤 사용자에게 전달하는 최종 알림이다. |

## 자주 헷갈리는 구분

- `event`와 `alert`는 다르다. AI Runtime은 `event`를 만든다.
- 최종 사용자에게 가는 `alert`의 정책과 전파는 Backend 책임이다.
- Frontend는 보통 Backend가 제공하는 데이터와 상태를 사용한다.

## 같이 보면 좋은 문서

- 시스템 경계도: [architecture.md](architecture.md)
- 공식 계약: [team_contract.md](team_contract.md)
- JSON과 표 예시: [schema_examples.md](schema_examples.md)
