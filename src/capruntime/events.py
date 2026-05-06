from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _normalize_sensor_status(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if not text:
        return None
    if text == "NORMAL":
        return "OK"
    if text == "WARNING":
        return "WARN"
    if text == "DANGER":
        return "ALERT"
    return text


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _infer_sensor_type(name: str) -> str:
    text = name.lower()
    if text.startswith("ultra"):
        return "ultrasonic"
    if "temp" in text:
        return "temperature"
    if "gas" in text:
        return "gas"
    return "generic"


def _infer_unit(name: str, sensor_type: str) -> str:
    text = sensor_type.lower()
    if text == "ultrasonic":
        return "m"
    if text == "temperature":
        return "celsius"
    if text == "gas":
        return "ppm"
    if "distance" in name.lower():
        return "m"
    return ""


def _sensor_status(payload: dict, value: float | None) -> str:
    status = _normalize_sensor_status(payload.get("status"))
    if status is not None:
        return status

    data = payload.get("data")
    if isinstance(data, dict):
        status = _normalize_sensor_status(data.get("status"))
        if status is not None:
            return status

    return "OK" if value is not None else "UNKNOWN"


def _event_sensor_payload(
    sensor_snapshot: dict[str, dict],
    status_overrides: dict[str, str],
) -> dict[str, dict[str, Any]]:
    sensors: dict[str, dict[str, Any]] = {}
    for name, payload in sensor_snapshot.items():
        if not isinstance(payload, dict):
            payload = {"data": payload}
        data = payload.get("data")
        if not isinstance(data, dict):
            data = {}

        value = _sensor_value(payload)
        sensor_type = str(payload.get("type") or data.get("type") or _infer_sensor_type(name)).strip().lower()
        unit = str(payload.get("unit") or data.get("unit") or _infer_unit(name, sensor_type))
        status = _normalize_sensor_status(status_overrides.get(name)) or _sensor_status(payload, value)
        sensors[name] = {
            "id": str(payload.get("id") or data.get("id") or name),
            "type": sensor_type,
            "ts": payload.get("ts") or data.get("ts"),
            "status": status,
            "unit": unit,
            "value": value,
        }
    return sensors


def _reason_from_detection(detection: dict[str, Any], zone: dict[str, Any]) -> dict[str, list[str] | str]:
    reason = detection.get("reason")
    if isinstance(reason, dict):
        code = str(reason.get("code") or detection.get("event_type", "DETECTION"))
        raw_factors = reason.get("factors", [])
    else:
        code = str(detection.get("reason_code") or detection.get("event_type", "DETECTION"))
        raw_factors = detection.get("reason_factors", detection.get("factors", []))

    factors = [str(item) for item in raw_factors if str(item).strip()] if isinstance(raw_factors, list) else []
    if not factors:
        if str(detection.get("object_type", "")).upper() == "PERSON":
            factors.append("PERSON_DETECTED")
        if bool(zone.get("inside", False)):
            factors.append("ZONE_INTRUSION")
        event_type = str(detection.get("event_type", "DETECTION")).upper()
        if event_type != "DETECTION":
            factors.append(event_type)
    return {"code": code, "factors": factors}


def build_event(
    site_id: str,
    camera_id: str,
    detection: dict[str, Any],
    sensor_snapshot: dict[str, dict],
    frame_id: int | None = None,
    frame_ts: str | None = None,
) -> dict[str, Any]:
    event_ts = _now_iso()
    bbox = detection.get("bbox", {})
    zone = detection.get("zone")
    if not isinstance(zone, dict):
        zone = {"zone_id": "", "inside": False}
    sensor_status_overrides = detection.get("sensor_status_overrides", {})
    if not isinstance(sensor_status_overrides, dict):
        sensor_status_overrides = {}
    return {
        "event_id": str(uuid4()),
        "ts": event_ts,
        "site_id": site_id,
        "camera_id": camera_id,
        "frame_id": detection.get("frame_id", frame_id),
        "frame_ts": str(detection.get("frame_ts") or frame_ts or event_ts),
        "event_type": detection.get("event_type", "DETECTION"),
        "event_status": str(detection.get("event_status", "ACTIVE")),
        "object_type": detection.get("object_type", "OBJECT"),
        "severity": detection.get("severity", "LOW"),
        "track_id": detection.get("track_id"),
        "confidence": float(detection.get("confidence", 0.0)),
        "bbox": {
            "x1": int(bbox.get("x1", 0)),
            "y1": int(bbox.get("y1", 0)),
            "x2": int(bbox.get("x2", 0)),
            "y2": int(bbox.get("y2", 0)),
        },
        "zone": {
            "zone_id": str(zone.get("zone_id", "")),
            "inside": bool(zone.get("inside", False)),
        },
        "reason": _reason_from_detection(detection, zone),
        "sensors": _event_sensor_payload(sensor_snapshot, status_overrides=sensor_status_overrides),
    }
