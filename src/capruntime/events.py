from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


_SENSOR_STATUS_ORDER = {
    "UNKNOWN": 0,
    "OK": 1,
    "NORMAL": 1,
    "WARN": 2,
    "WARNING": 2,
    "ALERT": 3,
    "DANGER": 3,
    "ERROR": 4,
    "OFFLINE": 4,
    "CRITICAL": 4,
}


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


def _strongest_sensor_status(statuses: list[str]) -> str | None:
    if not statuses:
        return None
    return max(statuses, key=lambda status: _SENSOR_STATUS_ORDER.get(status, 0))


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


def _backend_sensor_payload(sensor_snapshot: dict[str, dict]) -> dict[str, float]:
    # Current backend stores sensor_value as double precision, so send a numeric map.
    sensors: dict[str, float] = {}
    for name, payload in sensor_snapshot.items():
        value = _sensor_value(payload)
        if value is not None:
            sensors[name] = value
    return sensors


def _sensor_status(sensor_snapshot: dict[str, dict]) -> str:
    statuses: list[str] = []
    for payload in sensor_snapshot.values():
        if not isinstance(payload, dict):
            continue
        status = _normalize_sensor_status(payload.get("status"))
        if status is not None:
            statuses.append(status)

        data = payload.get("data")
        if isinstance(data, dict):
            status = _normalize_sensor_status(data.get("status"))
            if status is not None:
                statuses.append(status)

    strongest = _strongest_sensor_status(statuses)
    if strongest is not None:
        return strongest
    if sensor_snapshot:
        return "OK"
    return "UNKNOWN"


def build_event(
    site_id: str,
    camera_id: str,
    detection: dict[str, Any],
    sensor_snapshot: dict[str, dict],
) -> dict[str, Any]:
    bbox = detection.get("bbox", {})
    zone = detection.get("zone")
    if not isinstance(zone, dict):
        zone = {"zone_id": "", "inside": False}
    return {
        "event_id": str(uuid4()),
        "ts": _now_iso(),
        "site_id": site_id,
        "camera_id": camera_id,
        "event_type": detection.get("event_type", "DETECTION"),
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
        "sensor_status": str(detection.get("sensor_status") or _sensor_status(sensor_snapshot)),
        "sensors": _backend_sensor_payload(sensor_snapshot),
    }
