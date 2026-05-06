from __future__ import annotations

from typing import Any

import numpy as np

from .settings import DangerZoneSettings, SensorRuleSettings


_SEVERITY_ORDER = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}

_SENSOR_STATUS_BY_SEVERITY = {
    "LOW": "OK",
    "MEDIUM": "WARN",
    "HIGH": "ALERT",
    "CRITICAL": "CRITICAL",
}

def _stronger_severity(left: str, right: str) -> str:
    left_text = str(left or "LOW").upper()
    right_text = str(right or "LOW").upper()
    if _SEVERITY_ORDER.get(right_text, 0) > _SEVERITY_ORDER.get(left_text, 0):
        return right_text
    return left_text


def _sensor_value(payload: Any) -> float | None:
    if isinstance(payload, (int, float)):
        return float(payload)
    if not isinstance(payload, dict):
        return None

    data = payload.get("data", payload)
    if isinstance(data, dict):
        if isinstance(data.get("value"), (int, float)):
            return float(data["value"])
        numeric_values = [value for value in data.values() if isinstance(value, (int, float))]
        if len(numeric_values) == 1:
            return float(numeric_values[0])
    elif isinstance(data, (int, float)):
        return float(data)
    return None


def _bbox_center_norm(detection: dict, frame_shape: tuple[int, ...]) -> tuple[float, float] | None:
    if len(frame_shape) < 2:
        return None
    height, width = int(frame_shape[0]), int(frame_shape[1])
    if width <= 0 or height <= 0:
        return None

    bbox = detection.get("bbox", {})
    if not isinstance(bbox, dict):
        return None
    cx = (float(bbox.get("x1", 0)) + float(bbox.get("x2", 0))) / 2.0
    cy = (float(bbox.get("y1", 0)) + float(bbox.get("y2", 0))) / 2.0
    norm_x = (cx - width / 2.0) / (width / 2.0)
    norm_y = (height / 2.0 - cy) / (height / 2.0)
    return norm_x, norm_y


def _inside_quadrant(point: tuple[float, float], quadrant: int) -> bool:
    x, y = point
    if quadrant == 1:
        return x >= 0 and y >= 0
    if quadrant == 2:
        return x < 0 and y >= 0
    if quadrant == 3:
        return x < 0 and y < 0
    if quadrant == 4:
        return x >= 0 and y < 0
    return False


def _matching_zone(
    detection: dict,
    frame_shape: tuple[int, ...],
    danger_zones: list[DangerZoneSettings],
) -> DangerZoneSettings | None:
    if str(detection.get("object_type", "")).upper() != "PERSON":
        return None
    point = _bbox_center_norm(detection, frame_shape)
    if point is None:
        return None
    for zone in danger_zones:
        if zone.type == "quadrant" and _inside_quadrant(point, zone.quadrant):
            return zone
    return None


def evaluate_sensor_rules(
    sensor_snapshot: dict[str, dict],
    sensor_rules: list[SensorRuleSettings],
) -> list[dict]:
    hits: list[dict] = []
    for rule in sensor_rules:
        value = _sensor_value(sensor_snapshot.get(rule.sensor))
        if value is None:
            continue
        less_hit = rule.less_than is not None and value <= rule.less_than
        greater_hit = rule.greater_than is not None and value >= rule.greater_than
        if less_hit or greater_hit:
            hits.append(
                {
                    "sensor": rule.sensor,
                    "value": value,
                    "event_type": rule.event_type,
                    "severity": rule.severity,
                    "factor": f"{rule.sensor.upper()}_ALERT",
                    "status": _SENSOR_STATUS_BY_SEVERITY.get(str(rule.severity).upper(), "ALERT"),
                }
            )
    return hits


def apply_runtime_rules(
    detections: list[dict],
    frame: np.ndarray,
    sensor_snapshot: dict[str, dict],
    danger_zones: list[DangerZoneSettings],
    sensor_rules: list[SensorRuleSettings],
) -> list[dict]:
    sensor_hits = evaluate_sensor_rules(sensor_snapshot, sensor_rules)
    strongest_sensor_hit: dict | None = None
    for hit in sensor_hits:
        if strongest_sensor_hit is None:
            strongest_sensor_hit = hit
            continue
        if _SEVERITY_ORDER.get(str(hit["severity"]), 0) > _SEVERITY_ORDER.get(str(strongest_sensor_hit["severity"]), 0):
            strongest_sensor_hit = hit

    out: list[dict] = []
    sensor_status_overrides = {str(hit["sensor"]): str(hit["status"]) for hit in sensor_hits}
    sensor_factors = [str(hit["factor"]) for hit in sensor_hits]
    for detection in detections:
        enriched = dict(detection)
        reason_factors = [str(item) for item in enriched.get("reason_factors", [])]
        if str(enriched.get("object_type", "")).upper() == "PERSON" and "PERSON_DETECTED" not in reason_factors:
            reason_factors.append("PERSON_DETECTED")
        zone = _matching_zone(enriched, frame.shape, danger_zones)
        if zone is not None:
            enriched["event_type"] = "ZONE_INTRUSION"
            enriched["severity"] = _stronger_severity(enriched.get("severity", "LOW"), zone.severity)
            enriched["zone"] = {"zone_id": zone.zone_id, "inside": True}
            if "ZONE_INTRUSION" not in reason_factors:
                reason_factors.append("ZONE_INTRUSION")

        if strongest_sensor_hit is not None:
            if str(enriched.get("event_type", "DETECTION")).upper() == "DETECTION":
                enriched["event_type"] = str(strongest_sensor_hit["event_type"])
            enriched["severity"] = _stronger_severity(enriched.get("severity", "LOW"), str(strongest_sensor_hit["severity"]))
            for factor in sensor_factors:
                if factor not in reason_factors:
                    reason_factors.append(factor)
            enriched["sensor_status_overrides"] = sensor_status_overrides
        enriched["reason_code"] = str(enriched.get("event_type", "DETECTION")).upper()
        enriched["reason_factors"] = reason_factors
        out.append(enriched)

    if not out and strongest_sensor_hit is not None:
        out.append(
            {
                "event_type": str(strongest_sensor_hit["event_type"]),
                "object_type": "SENSOR",
                "severity": str(strongest_sensor_hit["severity"]),
                "confidence": 1.0,
                "bbox": {"x1": 0, "y1": 0, "x2": 0, "y2": 0},
                "track_id": None,
                "reason_code": str(strongest_sensor_hit["event_type"]).upper(),
                "reason_factors": sensor_factors,
                "sensor_status_overrides": sensor_status_overrides,
            }
        )
    return out
