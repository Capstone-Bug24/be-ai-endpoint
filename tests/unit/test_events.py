from __future__ import annotations

from capruntime.events import build_event


def test_build_event_sends_backend_numeric_sensor_map() -> None:
    event = build_event(
        site_id="S001",
        camera_id="cam01",
        detection={"bbox": {}, "confidence": 0.75},
        sensor_snapshot={
            "ultra_front": {
                "sensor": "ultra_front",
                "ts": "2026-05-06T00:00:00Z",
                "data": {"distance_m": 1.2, "status": "ok"},
            },
            "ultra_rear": {"data": {"value": 2.4}},
            "note_only": {"data": {"status": "warn"}},
        },
    )

    assert event["sensors"] == {
        "ultra_front": 1.2,
        "ultra_rear": 2.4,
    }
    assert event["sensor_status"] == "WARN"


def test_build_event_keeps_sensor_status_outside_sensors() -> None:
    event = build_event(
        site_id="S001",
        camera_id="cam01",
        detection={"bbox": {}, "confidence": 0.75, "sensor_status": "ALERT"},
        sensor_snapshot={
            "ultra_front": {
                "sensor": "ultra_front",
                "ts": "2026-05-06T00:00:00Z",
                "data": {"distance_m": 0.8, "status": "warn"},
            }
        },
    )

    assert event["sensor_status"] == "ALERT"
    assert event["sensors"] == {"ultra_front": 0.8}
    assert all(not isinstance(value, dict) for value in event["sensors"].values())
