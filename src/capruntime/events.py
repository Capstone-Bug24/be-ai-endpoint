from __future__ import annotations



from datetime import datetime, timezone

from typing import Any, Iterable

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






def _zone_ids_from_sensor(payload: dict[str, Any], data: dict[str, Any]) -> list[str]:
    raw = payload.get("zone_ids", data.get("zone_ids"))
    if raw is None:
        raw = payload.get("zone_id", data.get("zone_id"))
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    text = str(raw).strip()
    return [text] if text else []


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

        sensor_payload: dict[str, Any] = {

            "id": str(payload.get("id") or data.get("id") or name),

            "type": sensor_type,

            "ts": payload.get("ts") or data.get("ts"),

            "status": status,

            "unit": unit,

            "value": value,

        }

        zone_ids = _zone_ids_from_sensor(payload, data)

        if zone_ids:

            sensor_payload["zone_ids"] = zone_ids

        sensors[name] = sensor_payload

    return sensors





def _reason_from_detection(detection: dict[str, Any], zones: list[dict[str, Any]]) -> dict[str, list[str] | str]:
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

        if any(bool(zone.get("inside", False)) for zone in zones):
            factors.append("ZONE_INTRUSION")

        event_type = str(detection.get("event_type", "DETECTION")).upper()

        if event_type != "DETECTION":

            factors.append(event_type)

    return {"code": code, "factors": factors}





def _bbox_payload(detection: dict[str, Any]) -> dict[str, int]:

    bbox = detection.get("bbox", {})

    if not isinstance(bbox, dict):

        bbox = {}

    return {

        "x1": int(bbox.get("x1", 0)),

        "y1": int(bbox.get("y1", 0)),

        "x2": int(bbox.get("x2", 0)),

        "y2": int(bbox.get("y2", 0)),

    }


def _bbox_norm_payload(
    bbox: dict[str, int],
    frame_width: int | None,
    frame_height: int | None,
) -> dict[str, float] | None:
    if not frame_width or not frame_height or frame_width <= 0 or frame_height <= 0:
        return None

    def normalize(value: int, size: int) -> float:
        return round(max(0.0, min(1.0, float(value) / float(size))), 6)

    return {
        "x1": normalize(bbox["x1"], frame_width),
        "y1": normalize(bbox["y1"], frame_height),
        "x2": normalize(bbox["x2"], frame_width),
        "y2": normalize(bbox["y2"], frame_height),
    }





def _normalize_zone(zone: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "zone_id": str(zone.get("zone_id", "")),
        "inside": bool(zone.get("inside", False)),
    }
    zone_type = zone.get("zone_type") or zone.get("type")
    if zone_type:
        payload["zone_type"] = str(zone_type)
    basis = zone.get("basis")
    if basis:
        payload["basis"] = str(basis)
    if zone.get("overlap_ratio") is not None:
        payload["overlap_ratio"] = zone.get("overlap_ratio")
    return payload


def _zone_payloads(detection: dict[str, Any]) -> list[dict[str, Any]]:
    zones = detection.get("zones")
    if isinstance(zones, list):
        return [_normalize_zone(zone) for zone in zones if isinstance(zone, dict)]

    zone = detection.get("zone")
    if isinstance(zone, dict):
        normalized = _normalize_zone(zone)
        if normalized["zone_id"] or normalized["inside"]:
            return [normalized]
    return []


def _primary_zone_payload(zones: list[dict[str, Any]]) -> dict[str, Any]:
    for zone in zones:
        if bool(zone.get("inside", False)):
            return zone
    if zones:
        return zones[0]
    return {"zone_id": "", "inside": False}

def _collect_sensor_overrides(detections: Iterable[dict[str, Any]]) -> dict[str, str]:

    overrides: dict[str, str] = {}

    for detection in detections:

        raw = detection.get("sensor_status_overrides", {})

        if not isinstance(raw, dict):

            continue

        for name, status in raw.items():

            normalized = _normalize_sensor_status(status)

            if normalized is not None:

                overrides[str(name)] = normalized

    return overrides





def _sensor_refs(sensors: dict[str, dict[str, Any]]) -> list[str]:

    refs = []

    for name, sensor in sensors.items():

        status = str(sensor.get("status", "UNKNOWN")).upper()

        if status not in {"OK", "UNKNOWN"}:

            refs.append(name)

    return refs




def _sensor_zone_refs(sensors: dict[str, dict[str, Any]], sensor_refs: list[str]) -> list[str]:

    refs: list[str] = []

    for name in sensor_refs:

        sensor = sensors.get(name, {})

        zone_ids = sensor.get("zone_ids", [])

        if not isinstance(zone_ids, list):

            continue

        for zone_id in zone_ids:

            text = str(zone_id).strip()

            if text and text not in refs:

                refs.append(text)

    return refs


def _zone_refs(zones: list[dict[str, Any]]) -> list[str]:

    refs: list[str] = []

    for zone in zones:

        if not bool(zone.get("inside", False)):

            continue

        zone_id = str(zone.get("zone_id", "")).strip()

        if zone_id and zone_id not in refs:

            refs.append(zone_id)

    return refs


def _zone_evidence_payloads(detection_id: str, zones: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for zone in zones:
        zone_id = str(zone.get("zone_id", "")).strip()
        if not zone_id:
            continue
        item = {
            "type": "zone_match",
            "detection_id": detection_id,
            "zone_id": zone_id,
            "inside": bool(zone.get("inside", False)),
            "basis": str(zone.get("basis", "bbox_center")),
        }
        if zone.get("overlap_ratio") is not None:
            item["overlap_ratio"] = zone.get("overlap_ratio")
        evidence.append(item)
    return evidence


def _zone_points_from_norm(
    points_norm: Any,
    frame_width: int | None,
    frame_height: int | None,
) -> list[dict[str, int]]:
    if not frame_width or not frame_height or frame_width <= 0 or frame_height <= 0:
        return []
    if not isinstance(points_norm, list):
        return []

    points: list[dict[str, int]] = []
    for point in points_norm:
        if not isinstance(point, dict):
            continue
        try:
            x_norm = float(point["x"])
            y_norm = float(point["y"])
        except (KeyError, TypeError, ValueError):
            continue
        x_norm = max(0.0, min(1.0, x_norm))
        y_norm = max(0.0, min(1.0, y_norm))
        points.append(
            {
                "x": int(round(x_norm * frame_width)),
                "y": int(round(y_norm * frame_height)),
            }
        )
    return points


def _zone_definition_payloads(
    zone_definitions: list[dict[str, Any]] | None,
    frame_width: int | None,
    frame_height: int | None,
) -> list[dict[str, Any]]:
    if not isinstance(zone_definitions, list):
        return []
    zones: list[dict[str, Any]] = []
    for zone in zone_definitions:
        if not isinstance(zone, dict):
            continue
        zone_id = str(zone.get("zone_id", "")).strip()
        if not zone_id:
            continue

        points_norm = zone.get("points_norm", [])
        points = zone.get("points")
        if not isinstance(points, list):
            points = _zone_points_from_norm(points_norm, frame_width, frame_height)

        payload: dict[str, Any] = {"zone_id": zone_id}
        for key in ("name", "zone_type", "severity", "quadrant"):
            if key in zone and zone[key] is not None:
                payload[key] = zone[key]
        payload["points"] = points
        payload["points_norm"] = points_norm if isinstance(points_norm, list) else []
        for key, value in zone.items():
            if key not in payload and key != "points":
                payload[key] = value
        payload["zone_id"] = zone_id
        zones.append(payload)
    return zones


def _join_refs(refs: list[Any]) -> str:

    return ", ".join(str(ref) for ref in refs if str(ref).strip())


def _alert_message(alert: dict[str, Any]) -> str:

    event_type = str(alert.get("event_type", "DETECTION")).upper()

    object_refs = alert.get("object_refs", [])

    sensor_refs = alert.get("sensor_refs", [])

    zone_refs = alert.get("zone_refs", [])

    object_count = len(object_refs) if isinstance(object_refs, list) else 0

    sensor_text = _join_refs(sensor_refs) if isinstance(sensor_refs, list) else ""

    zone_text = _join_refs(zone_refs) if isinstance(zone_refs, list) else ""

    if event_type == "ZONE_INTRUSION":

        if object_count and zone_text:

            return f"작업자 {object_count}명 {zone_text} 진입 감지"

        if object_count:

            return f"작업자 {object_count}명 위험구역 진입 감지"

        return "위험구역 진입 감지"

    if event_type == "PROXIMITY_RISK":

        if object_count and sensor_text:

            return f"작업자 {object_count}명 주변 {sensor_text} 근접 위험 감지"

        if sensor_text:

            return f"{sensor_text} 근접 위험 감지"

        return "근접 위험 감지"

    if event_type in {"PPE_MISSING", "HELMET_MISSING", "SAFETY_HELMET_MISSING"}:

        if object_count:

            return f"작업자 {object_count}명 보호구 미착용 감지"

        return "보호구 미착용 감지"

    if object_count:

        return f"작업자 {object_count}명 {event_type} 감지"

    return f"{event_type} 감지"





def build_event(

    site_id: str,

    camera_id: str,

    detection: dict[str, Any],

    sensor_snapshot: dict[str, dict],

    frame_id: int | None = None,

    frame_ts: str | None = None,

) -> dict[str, Any]:

    """Legacy single-detection event payload.



    Keep this for tests, older backend code, and transitional tooling. The runtime

    now emits build_analysis_result() so multiple detections share one frame payload.

    """

    event_ts = _now_iso()

    zones = _zone_payloads(detection)

    zone = _primary_zone_payload(zones)

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

        "bbox": _bbox_payload(detection),

        "zone": zone,

        "zones": zones,

        "reason": _reason_from_detection(detection, zones),

        "sensors": _event_sensor_payload(sensor_snapshot, status_overrides=sensor_status_overrides),

    }





def build_analysis_result(

    site_id: str,

    camera_id: str,

    detections: list[dict[str, Any]],

    sensor_snapshot: dict[str, dict],

    frame_id: int | None = None,

    frame_ts: str | None = None,

    frame_ts_source: str | None = None,

    frame_shape: tuple[int, ...] | None = None,

    zone_definitions: list[dict[str, Any]] | None = None,

) -> dict[str, Any]:

    """Frame-level AI payload.



    One JSON object represents one analyzed frame. Visual objects live in

    detections[], the sensor snapshot is shared, and alert decisions live in

    alerts[] so frontend/backend do not have to reassemble per-object messages.

    """

    analysis_ts = _now_iso()

    analysis_id = str(uuid4())

    sensors = _event_sensor_payload(

        sensor_snapshot,

        status_overrides=_collect_sensor_overrides(detections),

    )

    sensor_refs = _sensor_refs(sensors)

    sensor_zone_refs = _sensor_zone_refs(sensors, sensor_refs)

    height = int(frame_shape[0]) if frame_shape and len(frame_shape) >= 2 else None

    width = int(frame_shape[1]) if frame_shape and len(frame_shape) >= 2 else None



    detection_payloads: list[dict[str, Any]] = []

    alert_groups: dict[tuple[str, str, str, tuple[str, ...]], dict[str, Any]] = {}



    for index, detection in enumerate(detections, start=1):

        zones = _zone_payloads(detection)

        zone_refs = _zone_refs(zones)

        reason = _reason_from_detection(detection, zones)

        event_type = str(detection.get("event_type", "DETECTION")).upper()

        severity = str(detection.get("severity", "LOW")).upper()

        object_type = str(detection.get("object_type", "OBJECT")).upper()

        is_visual_detection = object_type != "SENSOR"

        detection_id = str(detection.get("detection_id") or f"{analysis_id}:det-{index}")

        zone_evidence = _zone_evidence_payloads(detection_id, zones)



        if is_visual_detection:
            bbox = _bbox_payload(detection)

            detection_payloads.append(

                {

                    "detection_id": detection_id,

                    "object_type": object_type,

                    "confidence": float(detection.get("confidence", 0.0)),

                    "track_id": detection.get("track_id"),

                    "bbox": bbox,

                    "bbox_norm": _bbox_norm_payload(bbox, width, height),

                }

            )



        if event_type == "DETECTION":

            continue



        factors = tuple(str(item) for item in reason.get("factors", []))

        key = (event_type, severity, str(reason.get("code", event_type)), factors)

        if key not in alert_groups:

            alert_groups[key] = {

                "alert_id": str(uuid4()),

                "event_type": event_type,

                "event_status": str(detection.get("event_status", "ACTIVE")),

                "severity": severity,

                "object_refs": [],

                "sensor_refs": sensor_refs,

                "zone_refs": list(sensor_zone_refs),

                "evidence": [],

                "reason": reason,

            }

        if is_visual_detection:

            alert_groups[key]["object_refs"].append(detection_id)

        for zone_id in zone_refs:

            if zone_id not in alert_groups[key]["zone_refs"]:

                alert_groups[key]["zone_refs"].append(zone_id)

        for item in zone_evidence:

            alert_groups[key]["evidence"].append(item)


    alerts = list(alert_groups.values())

    for alert in alerts:

        alert["message"] = _alert_message(alert)


    return {

        "analysis_id": analysis_id,

        "ts": analysis_ts,

        "site_id": site_id,

        "camera_id": camera_id,

        "frame_id": frame_id,

        "frame_ts": str(frame_ts or analysis_ts),

        "frame_ts_source": str(frame_ts_source or ("provided" if frame_ts else "ai_payload_time")),

        "frame_width": width,

        "frame_height": height,

        "zones": _zone_definition_payloads(zone_definitions, width, height),

        "detections": detection_payloads,

        "sensors": sensors,

        "alerts": alerts,

    }
