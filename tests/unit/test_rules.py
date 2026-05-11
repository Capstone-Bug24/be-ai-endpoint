from __future__ import annotations

import numpy as np

from capruntime.rules import apply_runtime_rules, evaluate_sensor_rules
from capruntime.settings import DangerZoneSettings, SensorRuleSettings


def test_quadrant_rule_marks_person_inside_zone() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    detections = [
        {
            "event_type": "DETECTION",
            "object_type": "PERSON",
            "severity": "LOW",
            "confidence": 0.9,
            "bbox": {"x1": 70, "y1": 10, "x2": 90, "y2": 30},
        }
    ]

    events = apply_runtime_rules(
        detections=detections,
        frame=frame,
        sensor_snapshot={},
        danger_zones=[DangerZoneSettings(zone_id="danger_q1", quadrant=1, severity="MEDIUM")],
        sensor_rules=[],
    )

    assert events[0]["event_type"] == "ZONE_INTRUSION"
    assert events[0]["severity"] == "MEDIUM"
    assert events[0]["zone"] == {"zone_id": "danger_q1", "inside": True, "zone_type": "quadrant"}
    assert events[0]["zones"] == [{"zone_id": "danger_q1", "inside": True, "zone_type": "quadrant"}]

def test_quadrant_rule_can_return_multiple_matching_zones() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    detections = [
        {
            "event_type": "DETECTION",
            "object_type": "PERSON",
            "severity": "LOW",
            "confidence": 0.9,
            "bbox": {"x1": 70, "y1": 10, "x2": 90, "y2": 30},
        }
    ]

    events = apply_runtime_rules(
        detections=detections,
        frame=frame,
        sensor_snapshot={},
        danger_zones=[
            DangerZoneSettings(zone_id="danger_q1", quadrant=1, severity="MEDIUM"),
            DangerZoneSettings(zone_id="forklift_lane", quadrant=1, severity="HIGH"),
        ],
        sensor_rules=[],
    )

    assert events[0]["severity"] == "HIGH"
    assert events[0]["zones"] == [
        {"zone_id": "danger_q1", "inside": True, "zone_type": "quadrant"},
        {"zone_id": "forklift_lane", "inside": True, "zone_type": "quadrant"},
    ]



def test_sensor_threshold_rule_marks_close_distance() -> None:
    hits = evaluate_sensor_rules(
        sensor_snapshot={
            "ultra_front": {
                "sensor": "ultra_front",
                "data": {"distance_m": 1.2, "status": "ok"},
            }
        },
        sensor_rules=[SensorRuleSettings(sensor="ultra_front", less_than=1.5, severity="HIGH")],
    )

    assert hits == [
        {
            "sensor": "ultra_front",
            "value": 1.2,
            "event_type": "PROXIMITY_RISK",
            "severity": "HIGH",
            "factor": "ULTRA_FRONT_ALERT",
            "status": "ALERT",
        }
    ]


def test_sensor_only_rule_emits_risk_event() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    events = apply_runtime_rules(
        detections=[],
        frame=frame,
        sensor_snapshot={"ultra_front": {"data": {"distance_m": 0.8}}},
        danger_zones=[],
        sensor_rules=[SensorRuleSettings(sensor="ultra_front", less_than=1.0, severity="HIGH")],
    )

    assert events[0]["event_type"] == "PROXIMITY_RISK"
    assert events[0]["object_type"] == "SENSOR"
    assert events[0]["severity"] == "HIGH"
    assert events[0]["reason_code"] == "PROXIMITY_RISK"
    assert events[0]["reason_factors"] == ["ULTRA_FRONT_ALERT"]
    assert events[0]["sensor_status_overrides"] == {"ultra_front": "ALERT"}
