from __future__ import annotations

import numpy as np

from capruntime.rules import (
    apply_runtime_rules,
    evaluate_ppe_rules,
    evaluate_sensor_rules,
)
from capruntime.settings import DangerZoneSettings, PpeRuleSettings, SensorRuleSettings


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
        danger_zones=[
            DangerZoneSettings(zone_id="danger_q1", quadrant=1, severity="MEDIUM")
        ],
        sensor_rules=[],
    )

    assert events[0]["event_type"] == "ZONE_INTRUSION"
    assert events[0]["severity"] == "MEDIUM"
    assert events[0]["zone"] == {
        "zone_id": "danger_q1",
        "inside": True,
        "zone_type": "quadrant",
        "basis": "bbox_bottom_band",
        "overlap_ratio": 1.0,
    }
    assert events[0]["zones"] == [events[0]["zone"]]


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
        {
            "zone_id": "danger_q1",
            "inside": True,
            "zone_type": "quadrant",
            "basis": "bbox_bottom_band",
            "overlap_ratio": 1.0,
        },
        {
            "zone_id": "forklift_lane",
            "inside": True,
            "zone_type": "quadrant",
            "basis": "bbox_bottom_band",
            "overlap_ratio": 1.0,
        },
    ]


def test_sensor_threshold_rule_marks_close_distance() -> None:
    hits = evaluate_sensor_rules(
        sensor_snapshot={
            "ultra_front": {
                "sensor": "ultra_front",
                "data": {"distance_m": 1.2, "status": "ok"},
            }
        },
        sensor_rules=[
            SensorRuleSettings(sensor="ultra_front", less_than=1.5, severity="HIGH")
        ],
    )

    assert hits == [
        {
            "sensor": "ultra_front",
            "value": 1.2,
            "event_type": "PROXIMITY_RISK",
            "severity": "HIGH",
            "factor": "ULTRA_FRONT_ALERT",
            "status": "ALERT",
            "zone_ids": [],
        }
    ]


def test_sensor_only_rule_emits_risk_event() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    events = apply_runtime_rules(
        detections=[],
        frame=frame,
        sensor_snapshot={"ultra_front": {"data": {"distance_m": 0.8}}},
        danger_zones=[],
        sensor_rules=[
            SensorRuleSettings(sensor="ultra_front", less_than=1.0, severity="HIGH")
        ],
    )

    assert events[0]["event_type"] == "PROXIMITY_RISK"
    assert events[0]["object_type"] == "SENSOR"
    assert events[0]["severity"] == "HIGH"
    assert events[0]["reason_code"] == "PROXIMITY_RISK"
    assert events[0]["reason_factors"] == ["ULTRA_FRONT_ALERT"]
    assert events[0]["sensor_status_overrides"] == {"ultra_front": "ALERT"}


def test_ppe_rule_marks_direct_no_helmet_detection() -> None:
    detections = [
        {
            "event_type": "DETECTION",
            "object_type": "PERSON",
            "severity": "LOW",
            "confidence": 0.9,
            "bbox": {"x1": 10, "y1": 10, "x2": 110, "y2": 210},
        },
        {
            "event_type": "DETECTION",
            "object_type": "NO_HELMET",
            "severity": "MEDIUM",
            "confidence": 0.82,
            "bbox": {"x1": 35, "y1": 12, "x2": 82, "y2": 62},
        },
    ]

    alerts = evaluate_ppe_rules(
        detections,
        PpeRuleSettings(enabled=True, required=("helmet",), severity="HIGH"),
    )

    assert len(alerts) == 1
    assert alerts[0]["event_type"] == "HELMET_MISSING"
    assert alerts[0]["severity"] == "HIGH"
    assert alerts[0]["ppe"]["missing"] == ["helmet"]
    assert "HELMET_MISSING" in alerts[0]["reason_factors"]


def test_ppe_rule_does_not_infer_missing_by_default() -> None:
    detections = [
        {
            "event_type": "DETECTION",
            "object_type": "PERSON",
            "severity": "LOW",
            "confidence": 0.9,
            "bbox": {"x1": 10, "y1": 10, "x2": 110, "y2": 210},
        }
    ]

    alerts = evaluate_ppe_rules(
        detections,
        PpeRuleSettings(
            enabled=True, required=("helmet",), infer_missing_when_absent=False
        ),
    )

    assert alerts == []


def test_runtime_rules_add_ppe_alert_without_removing_person_detection() -> None:
    frame = np.zeros((240, 160, 3), dtype=np.uint8)
    detections = [
        {
            "event_type": "DETECTION",
            "object_type": "PERSON",
            "severity": "LOW",
            "confidence": 0.9,
            "bbox": {"x1": 10, "y1": 10, "x2": 110, "y2": 210},
        },
        {
            "event_type": "DETECTION",
            "object_type": "NO_VEST",
            "severity": "MEDIUM",
            "confidence": 0.8,
            "bbox": {"x1": 25, "y1": 70, "x2": 95, "y2": 155},
        },
    ]

    events = apply_runtime_rules(
        detections=detections,
        frame=frame,
        sensor_snapshot={},
        danger_zones=[],
        sensor_rules=[],
        ppe_rules=PpeRuleSettings(enabled=True, required=("vest",), severity="HIGH"),
    )

    assert [event["event_type"] for event in events] == [
        "DETECTION",
        "DETECTION",
        "VEST_MISSING",
    ]


def test_sensor_rule_does_not_attach_to_non_person_detection() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    events = apply_runtime_rules(
        detections=[
            {
                "event_type": "DETECTION",
                "object_type": "HELMET",
                "severity": "LOW",
                "confidence": 0.8,
                "bbox": {"x1": 10, "y1": 10, "x2": 30, "y2": 30},
            }
        ],
        frame=frame,
        sensor_snapshot={"ultra_front": {"data": {"distance_m": 0.8}}},
        danger_zones=[],
        sensor_rules=[
            SensorRuleSettings(sensor="ultra_front", less_than=1.0, severity="HIGH")
        ],
    )

    assert events[0]["event_type"] == "DETECTION"
    assert events[1]["event_type"] == "PROXIMITY_RISK"
    assert events[1]["object_type"] == "SENSOR"


def test_sensor_rule_attaches_only_to_matching_zone() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    events = apply_runtime_rules(
        detections=[
            {
                "event_type": "DETECTION",
                "object_type": "PERSON",
                "severity": "LOW",
                "confidence": 0.9,
                "bbox": {"x1": 70, "y1": 10, "x2": 90, "y2": 30},
            },
            {
                "event_type": "DETECTION",
                "object_type": "PERSON",
                "severity": "LOW",
                "confidence": 0.9,
                "bbox": {"x1": 10, "y1": 70, "x2": 30, "y2": 90},
            },
        ],
        frame=frame,
        sensor_snapshot={
            "ultra_front": {
                "data": {"distance_m": 0.8},
                "zone_ids": ["danger_q1"],
            }
        },
        danger_zones=[
            DangerZoneSettings(zone_id="danger_q1", quadrant=1, severity="MEDIUM"),
            DangerZoneSettings(zone_id="danger_q3", quadrant=3, severity="MEDIUM"),
        ],
        sensor_rules=[
            SensorRuleSettings(sensor="ultra_front", less_than=1.0, severity="HIGH")
        ],
    )

    assert events[0]["event_type"] == "ZONE_INTRUSION"
    assert events[0]["sensor_status_overrides"] == {"ultra_front": "ALERT"}
    assert events[1]["event_type"] == "ZONE_INTRUSION"
    assert "sensor_status_overrides" not in events[1]
