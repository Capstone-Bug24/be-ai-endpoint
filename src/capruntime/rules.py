from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .settings import DangerZoneSettings, PpeRuleSettings, SensorRuleSettings


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

_PPE_WORN_TYPES = {
    "helmet": {"HELMET"},
    "vest": {"VEST"},
    "mask": {"MASK"},
    "goggles": {"GOGGLES"},
    "gloves": {"GLOVES"},
    "boots": {"BOOTS"},
}

_PPE_MISSING_TYPES = {
    "helmet": {"NO_HELMET"},
    "vest": {"NO_VEST"},
    "mask": {"NO_MASK"},
    "goggles": {"NO_GOGGLES"},
    "gloves": {"NO_GLOVES"},
    "boots": {"NO_BOOTS"},
}

_PPE_EVENT_TYPES = {
    "helmet": "HELMET_MISSING",
    "vest": "VEST_MISSING",
    "mask": "MASK_MISSING",
    "goggles": "GOGGLES_MISSING",
    "gloves": "GLOVES_MISSING",
    "boots": "BOOTS_MISSING",
}


@dataclass(frozen=True)
class ZoneMatch:
    zone: DangerZoneSettings
    overlap_ratio: float


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
        numeric_values = [
            value for value in data.values() if isinstance(value, (int, float))
        ]
        if len(numeric_values) == 1:
            return float(numeric_values[0])
    elif isinstance(data, (int, float)):
        return float(data)
    return None


def _sensor_zone_ids(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    raw = payload.get("zone_ids", [])
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    zone_ids: list[str] = []
    for item in raw:
        text = str(item).strip()
        if text and text not in zone_ids:
            zone_ids.append(text)
    return zone_ids


def _detection_zone_ids(detection: dict) -> list[str]:
    zones = detection.get("zones", [])
    if isinstance(zones, dict):
        zones = [zones]
    if not isinstance(zones, list):
        return []
    zone_ids: list[str] = []
    for zone in zones:
        if not isinstance(zone, dict) or not bool(zone.get("inside", False)):
            continue
        zone_id = str(zone.get("zone_id", "")).strip()
        if zone_id and zone_id not in zone_ids:
            zone_ids.append(zone_id)
    return zone_ids


def _sensor_hit_applies_to_detection(detection: dict, sensor_hit: dict) -> bool:
    sensor_zones = [str(zone_id) for zone_id in sensor_hit.get("zone_ids", [])]
    if not sensor_zones:
        return False
    detection_zones = set(_detection_zone_ids(detection))
    return any(zone_id in detection_zones for zone_id in sensor_zones)


def _bbox_bottom_center(
    detection: dict, frame_shape: tuple[int, ...]
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]] | None:
    if len(frame_shape) < 2:
        return None
    height, width = int(frame_shape[0]), int(frame_shape[1])
    if width <= 0 or height <= 0:
        return None

    bbox = _bbox(detection)
    if bbox is None:
        return None
    cx = (bbox["x1"] + bbox["x2"]) / 2.0
    foot_y = bbox["y2"]
    pixel = (cx, foot_y)
    norm = (
        max(0.0, min(1.0, cx / float(width))),
        max(0.0, min(1.0, foot_y / float(height))),
    )
    centered = (
        (cx - width / 2.0) / (width / 2.0),
        (height / 2.0 - foot_y) / (height / 2.0),
    )
    return pixel, norm, centered


def _bbox_foot_samples(
    detection: dict,
    frame_shape: tuple[int, ...],
    band_ratio: float,
) -> (
    tuple[
        list[tuple[float, float]], list[tuple[float, float]], list[tuple[float, float]]
    ]
    | None
):
    if len(frame_shape) < 2:
        return None
    height, width = int(frame_shape[0]), int(frame_shape[1])
    if width <= 0 or height <= 0:
        return None
    bbox = _bbox(detection)
    if bbox is None:
        return None

    ratio = max(0.05, min(0.5, float(band_ratio or 0.18)))
    band_y1 = bbox["y2"] - (bbox["y2"] - bbox["y1"]) * ratio
    xs = [
        bbox["x1"] + (bbox["x2"] - bbox["x1"]) * fraction
        for fraction in (0.2, 0.35, 0.5, 0.65, 0.8)
    ]
    ys = [band_y1 + (bbox["y2"] - band_y1) * fraction for fraction in (0.25, 0.6, 0.9)]

    pixel: list[tuple[float, float]] = []
    norm: list[tuple[float, float]] = []
    centered: list[tuple[float, float]] = []
    for y in ys:
        for x in xs:
            clamped_x = max(0.0, min(float(width), x))
            clamped_y = max(0.0, min(float(height), y))
            pixel.append((clamped_x, clamped_y))
            norm.append((clamped_x / float(width), clamped_y / float(height)))
            centered.append(
                (
                    (clamped_x - width / 2.0) / (width / 2.0),
                    (height / 2.0 - clamped_y) / (height / 2.0),
                )
            )
    return pixel, norm, centered


def _bbox(detection: dict) -> dict[str, float] | None:
    raw = detection.get("bbox", {})
    if not isinstance(raw, dict):
        return None
    try:
        x1 = float(raw["x1"])
        y1 = float(raw["y1"])
        x2 = float(raw["x2"])
        y2 = float(raw["y2"])
    except (KeyError, TypeError, ValueError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


def _bbox_area(box: dict[str, float]) -> float:
    return max(0.0, box["x2"] - box["x1"]) * max(0.0, box["y2"] - box["y1"])


def _intersection_ratio(inner: dict[str, float], outer: dict[str, float]) -> float:
    x1 = max(inner["x1"], outer["x1"])
    y1 = max(inner["y1"], outer["y1"])
    x2 = min(inner["x2"], outer["x2"])
    y2 = min(inner["y2"], outer["y2"])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return ((x2 - x1) * (y2 - y1)) / max(1.0, _bbox_area(inner))


def _person_region(person_box: dict[str, float], item: str) -> dict[str, float]:
    height = person_box["y2"] - person_box["y1"]
    if item == "helmet":
        return {
            "x1": person_box["x1"],
            "y1": person_box["y1"],
            "x2": person_box["x2"],
            "y2": person_box["y1"] + height * 0.35,
        }
    if item == "vest":
        return {
            "x1": person_box["x1"],
            "y1": person_box["y1"] + height * 0.20,
            "x2": person_box["x2"],
            "y2": person_box["y1"] + height * 0.75,
        }
    return person_box


def _matching_ppe(
    person: dict,
    detections: list[dict],
    item: str,
    object_types: set[str],
    min_confidence: float,
) -> tuple[bool, list[dict]]:
    person_box = _bbox(person)
    if person_box is None:
        return False, []
    region = _person_region(person_box, item)
    matches: list[dict] = []
    for detection in detections:
        object_type = str(detection.get("object_type", "")).upper()
        if object_type not in object_types:
            continue
        try:
            confidence = float(detection.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < min_confidence:
            continue
        ppe_box = _bbox(detection)
        if ppe_box is None:
            continue
        if _intersection_ratio(ppe_box, region) >= 0.35:
            matches.append(detection)
    return bool(matches), matches


def _detection_ref(detection: dict, fallback: str) -> str:
    return str(detection.get("detection_id") or detection.get("track_id") or fallback)


def evaluate_ppe_rules(
    detections: list[dict], ppe_rules: PpeRuleSettings
) -> list[dict]:
    if not ppe_rules.enabled:
        return []

    people = []
    for index, detection in enumerate(detections):
        if str(detection.get("object_type", "")).upper() != "PERSON":
            continue
        try:
            confidence = float(detection.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence >= ppe_rules.min_person_confidence:
            item = dict(detection)
            item["_ppe_person_index"] = index
            people.append(item)

    alerts: list[dict] = []
    for person in people:
        person_ref = _detection_ref(person, f"person-{person['_ppe_person_index']}")
        missing_items: list[str] = []
        worn_items: list[str] = []
        evidence: list[dict[str, Any]] = []

        for required in ppe_rules.required:
            item = str(required).strip().lower()
            worn_types = _PPE_WORN_TYPES.get(item)
            missing_types = _PPE_MISSING_TYPES.get(item)
            if not worn_types and not missing_types:
                continue

            has_missing_marker, missing_matches = _matching_ppe(
                person,
                detections,
                item,
                missing_types or set(),
                ppe_rules.min_ppe_confidence,
            )
            has_worn_marker, worn_matches = _matching_ppe(
                person,
                detections,
                item,
                worn_types or set(),
                ppe_rules.min_ppe_confidence,
            )

            for match in missing_matches:
                evidence.append(
                    {
                        "type": "ppe_match",
                        "person_ref": person_ref,
                        "ppe": item,
                        "status": "missing",
                        "object_type": str(match.get("object_type", "OBJECT")).upper(),
                        "confidence": float(match.get("confidence", 0.0)),
                    }
                )
            for match in worn_matches:
                evidence.append(
                    {
                        "type": "ppe_match",
                        "person_ref": person_ref,
                        "ppe": item,
                        "status": "worn",
                        "object_type": str(match.get("object_type", "OBJECT")).upper(),
                        "confidence": float(match.get("confidence", 0.0)),
                    }
                )

            if has_missing_marker:
                missing_items.append(item)
            elif has_worn_marker:
                worn_items.append(item)
            elif ppe_rules.infer_missing_when_absent:
                missing_items.append(item)
                evidence.append(
                    {
                        "type": "ppe_absence",
                        "person_ref": person_ref,
                        "ppe": item,
                        "status": "missing_candidate",
                    }
                )

        if not missing_items:
            continue

        if len(missing_items) == 1:
            event_type = _PPE_EVENT_TYPES.get(missing_items[0], "PPE_MISSING")
        else:
            event_type = "PPE_MISSING"
        reason_factors = ["PERSON_DETECTED", "PPE_CHECK"]
        for item in missing_items:
            reason_factors.append(f"{item.upper()}_MISSING")
        for item in worn_items:
            reason_factors.append(f"{item.upper()}_DETECTED")

        alert = dict(person)
        person_index = int(alert.pop("_ppe_person_index"))
        alert["event_type"] = event_type
        alert["suppress_detection"] = True
        alert["ref_detection_index"] = person_index
        alert["severity"] = ppe_rules.severity
        alert["reason_code"] = event_type
        alert["reason_factors"] = reason_factors
        alert["ppe"] = {
            "missing": missing_items,
            "worn": worn_items,
            "required": list(ppe_rules.required),
        }
        alert["ppe_evidence"] = evidence
        alerts.append(alert)
    return alerts


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


def _point_in_polygon(
    point: tuple[float, float], polygon: tuple[tuple[float, float], ...]
) -> bool:
    if len(polygon) < 3:
        return False
    x, y = point
    inside = False
    prev_x, prev_y = polygon[-1]
    for curr_x, curr_y in polygon:
        if (curr_y > y) != (prev_y > y):
            cross_x = ((prev_x - curr_x) * (y - curr_y) / (prev_y - curr_y)) + curr_x
            if x < cross_x:
                inside = not inside
        prev_x, prev_y = curr_x, curr_y
    return inside


def _match_ratio(points: list[tuple[float, float]], predicate) -> float:
    if not points:
        return 0.0
    hits = sum(1 for point in points if predicate(point))
    return hits / float(len(points))


def _matching_zones(
    detection: dict,
    frame_shape: tuple[int, ...],
    danger_zones: list[DangerZoneSettings],
) -> list[ZoneMatch]:
    if str(detection.get("object_type", "")).upper() != "PERSON":
        return []
    center_points = _bbox_bottom_center(detection, frame_shape)
    if center_points is None:
        return []
    foot_pixel, foot_norm, foot_centered = center_points
    matches: list[ZoneMatch] = []
    for zone in danger_zones:
        if zone.basis == "bbox_bottom_center":
            if zone.type == "quadrant" and _inside_quadrant(
                foot_centered, zone.quadrant
            ):
                matches.append(ZoneMatch(zone=zone, overlap_ratio=1.0))
            elif (
                zone.type == "polygon"
                and zone.points_norm
                and _point_in_polygon(foot_norm, zone.points_norm)
            ):
                matches.append(ZoneMatch(zone=zone, overlap_ratio=1.0))
            elif (
                zone.type == "polygon"
                and zone.points
                and _point_in_polygon(foot_pixel, zone.points)
            ):
                matches.append(ZoneMatch(zone=zone, overlap_ratio=1.0))
            continue

        samples = _bbox_foot_samples(detection, frame_shape, zone.foot_band_ratio)
        if samples is None:
            continue
        foot_pixels, foot_norms, foot_centered_points = samples
        min_ratio = max(0.0, min(1.0, float(zone.min_overlap_ratio)))
        if zone.type == "quadrant":
            ratio = _match_ratio(
                foot_centered_points,
                lambda point: _inside_quadrant(point, zone.quadrant),
            )
            if ratio >= min_ratio:
                matches.append(ZoneMatch(zone=zone, overlap_ratio=ratio))
        elif zone.type == "polygon" and zone.points_norm:
            ratio = _match_ratio(
                foot_norms, lambda point: _point_in_polygon(point, zone.points_norm)
            )
            if ratio >= min_ratio:
                matches.append(ZoneMatch(zone=zone, overlap_ratio=ratio))
        elif zone.type == "polygon" and zone.points:
            ratio = _match_ratio(
                foot_pixels, lambda point: _point_in_polygon(point, zone.points)
            )
            if ratio >= min_ratio:
                matches.append(ZoneMatch(zone=zone, overlap_ratio=ratio))
    return matches


def evaluate_sensor_rules(
    sensor_snapshot: dict[str, dict],
    sensor_rules: list[SensorRuleSettings],
) -> list[dict]:
    hits: list[dict] = []
    for rule in sensor_rules:
        sensor_payload = sensor_snapshot.get(rule.sensor)
        value = _sensor_value(sensor_payload)
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
                    "status": _SENSOR_STATUS_BY_SEVERITY.get(
                        str(rule.severity).upper(), "ALERT"
                    ),
                    "zone_ids": _sensor_zone_ids(sensor_payload),
                }
            )
    return hits


def apply_runtime_rules(
    detections: list[dict],
    frame: np.ndarray,
    sensor_snapshot: dict[str, dict],
    danger_zones: list[DangerZoneSettings],
    sensor_rules: list[SensorRuleSettings],
    ppe_rules: PpeRuleSettings | None = None,
) -> list[dict]:
    sensor_hits = evaluate_sensor_rules(sensor_snapshot, sensor_rules)
    strongest_sensor_hit: dict | None = None
    for hit in sensor_hits:
        if strongest_sensor_hit is None:
            strongest_sensor_hit = hit
            continue
        if _SEVERITY_ORDER.get(str(hit["severity"]), 0) > _SEVERITY_ORDER.get(
            str(strongest_sensor_hit["severity"]), 0
        ):
            strongest_sensor_hit = hit

    ppe_alerts = (
        evaluate_ppe_rules(detections, ppe_rules) if ppe_rules is not None else []
    )

    out: list[dict] = []
    sensor_status_overrides = {
        str(hit["sensor"]): str(hit["status"]) for hit in sensor_hits
    }
    sensor_factors = [str(hit["factor"]) for hit in sensor_hits]
    sensor_hit_attached = False
    for detection in detections:
        enriched = dict(detection)
        reason_factors = [str(item) for item in enriched.get("reason_factors", [])]
        is_person = str(enriched.get("object_type", "")).upper() == "PERSON"
        if is_person and "PERSON_DETECTED" not in reason_factors:
            reason_factors.append("PERSON_DETECTED")
        zone_matches = _matching_zones(enriched, frame.shape, danger_zones)
        if zone_matches:
            enriched["event_type"] = "ZONE_INTRUSION"
            for match in zone_matches:
                enriched["severity"] = _stronger_severity(
                    enriched.get("severity", "LOW"), match.zone.severity
                )
            enriched["zones"] = [
                {
                    "zone_id": match.zone.zone_id,
                    "inside": True,
                    "zone_type": match.zone.type,
                    "basis": match.zone.basis,
                    "overlap_ratio": round(match.overlap_ratio, 6),
                }
                for match in zone_matches
            ]
            enriched["zone"] = enriched["zones"][0]
            if "ZONE_INTRUSION" not in reason_factors:
                reason_factors.append("ZONE_INTRUSION")

        if (
            is_person
            and strongest_sensor_hit is not None
            and _sensor_hit_applies_to_detection(enriched, strongest_sensor_hit)
        ):
            if str(enriched.get("event_type", "DETECTION")).upper() == "DETECTION":
                enriched["event_type"] = str(strongest_sensor_hit["event_type"])
            enriched["severity"] = _stronger_severity(
                enriched.get("severity", "LOW"), str(strongest_sensor_hit["severity"])
            )
            for factor in sensor_factors:
                if factor not in reason_factors:
                    reason_factors.append(factor)
            enriched["sensor_status_overrides"] = sensor_status_overrides
            sensor_hit_attached = True
        enriched["reason_code"] = str(enriched.get("event_type", "DETECTION")).upper()
        enriched["reason_factors"] = reason_factors
        out.append(enriched)

    out.extend(ppe_alerts)

    if not sensor_hit_attached and strongest_sensor_hit is not None:
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
