from __future__ import annotations

from capruntime.events import build_event


def test_build_event_uses_final_sensor_object_map() -> None:
    event = build_event(
        site_id="S001",
        camera_id="cam01",
        detection={"bbox": {}, "confidence": 0.75, "reason_code": "PROXIMITY_RISK"},
        sensor_snapshot={
            "ultra_front": {
                "sensor": "ultra_front",
                "id": "ultra_front_01",
                "type": "ultrasonic",
                "ts": "2026-05-06T00:00:00Z",
                "unit": "m",
                "data": {"distance_m": 1.2, "status": "ok"},
            },
            "ultra_rear": {"data": {"value": 2.4}},
            "note_only": {"data": {"status": "warn"}},
        },
        frame_id=42,
        frame_ts="2026-05-06T00:00:01Z",
    )

    assert event["frame_id"] == 42
    assert event["frame_ts"] == "2026-05-06T00:00:01Z"
    assert event["event_status"] == "ACTIVE"
    assert event["reason"] == {"code": "PROXIMITY_RISK", "factors": []}
    assert "sensor_status" not in event
    assert event["sensors"]["ultra_front"] == {
        "id": "ultra_front_01",
        "type": "ultrasonic",
        "ts": "2026-05-06T00:00:00Z",
        "status": "OK",
        "unit": "m",
        "value": 1.2,
    }
    assert event["sensors"]["ultra_rear"]["value"] == 2.4
    assert event["sensors"]["note_only"]["status"] == "WARN"
    assert event["sensors"]["note_only"]["value"] is None


def test_build_event_keeps_sensor_status_inside_each_sensor() -> None:
    event = build_event(
        site_id="S001",
        camera_id="cam01",
        detection={"bbox": {}, "confidence": 0.75},
        sensor_snapshot={
            "ultra_front": {
                "sensor": "ultra_front",
                "ts": "2026-05-06T00:00:00Z",
                "data": {"distance_m": 0.8, "status": "warn"},
            }
        },
    )

    assert "sensor_status" not in event
    assert event["sensors"]["ultra_front"]["status"] == "WARN"
    assert event["sensors"]["ultra_front"]["value"] == 0.8


def test_build_event_applies_rule_sensor_status_override() -> None:
    event = build_event(
        site_id="S001",
        camera_id="cam01",
        detection={
            "bbox": {},
            "confidence": 0.75,
            "sensor_status_overrides": {"ultra_front": "ALERT"},
        },
        sensor_snapshot={"ultra_front": {"data": {"value": 1.5}}},
    )

    assert event["sensors"]["ultra_front"]["status"] == "ALERT"
