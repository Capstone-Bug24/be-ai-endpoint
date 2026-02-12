from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_event(
    site_id: str,
    camera_id: str,
    detection: dict[str, Any],
    sensor_snapshot: dict[str, dict],
) -> dict[str, Any]:
    bbox = detection.get("bbox", {})
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
        "zone": {"zone_id": "", "inside": False},
        "sensors": sensor_snapshot,
    }
