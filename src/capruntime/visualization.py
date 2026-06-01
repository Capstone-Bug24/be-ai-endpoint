from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import cv2
import numpy as np


def format_detection_label(detection: Mapping[str, Any]) -> str:
    object_type = str(detection.get("object_type", "OBJECT")).strip() or "OBJECT"
    event_type = str(detection.get("event_type", "")).strip()
    severity = str(detection.get("severity", "")).strip()
    zones = detection.get("zones", [])
    zone_ids: list[str] = []
    if isinstance(zones, Sequence) and not isinstance(zones, (str, bytes)):
        for zone in zones:
            if isinstance(zone, Mapping) and zone.get("inside"):
                zone_id = str(zone.get("zone_id", "")).strip()
                if zone_id and zone_id not in zone_ids:
                    zone_ids.append(zone_id)
    if not zone_ids:
        zone = detection.get("zone", {})
        if isinstance(zone, Mapping) and zone.get("inside"):
            zone_id = str(zone.get("zone_id", "")).strip()
            if zone_id:
                zone_ids.append(zone_id)
    confidence = detection.get("confidence")
    try:
        parts = [object_type, f"{float(confidence):.2f}"]
    except (TypeError, ValueError):
        parts = [object_type]
    if event_type:
        parts.append(event_type)
    if severity:
        parts.append(severity)
    if zone_ids:
        parts.append(",".join(zone_ids))
    return " ".join(parts)


def resolve_video_fps(capture_fps: float, default_fps: float = 10.0) -> float:
    if np.isfinite(capture_fps) and capture_fps > 0:
        return float(capture_fps)
    return float(default_fps)


def build_video_writer(
    output_path: str | Path, frame_size: tuple[int, int], fps: float
) -> cv2.VideoWriter:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(
        *("XVID" if path.suffix.lower() == ".avi" else "mp4v")
    )
    writer = cv2.VideoWriter(str(path), fourcc, fps, frame_size)
    if not writer.isOpened():
        raise RuntimeError(f"Unable to open output video writer: {path}")
    return writer


_PALETTE = [
    (66, 133, 244),
    (52, 168, 83),
    (251, 188, 5),
    (234, 67, 53),
    (171, 71, 188),
    (0, 172, 193),
    (255, 112, 67),
    (124, 179, 66),
]

_TRACKABLE_DISPLAY_TYPES = {
    "PERSON",
    "VEHICLE",
    "MACHINERY",
    "FORKLIFT",
    "TRUCK",
}

_PPE_BADGES = {
    "HELMET": ("helmet", "H"),
    "NO_HELMET": ("helmet", "!H"),
    "VEST": ("vest", "V"),
    "SAFETY_VEST": ("vest", "V"),
    "NO_VEST": ("vest", "!V"),
    "MASK": ("mask", "M"),
    "NO_MASK": ("mask", "!M"),
}

_PPE_BADGE_ORDER = ("helmet", "vest", "mask")


def _bbox_from_detection(detection: Mapping[str, Any]) -> dict[str, float] | None:
    bbox = detection.get("bbox", {})
    if not isinstance(bbox, Mapping):
        return None
    try:
        x1 = float(bbox["x1"])
        y1 = float(bbox["y1"])
        x2 = float(bbox["x2"])
        y2 = float(bbox["y2"])
    except (KeyError, TypeError, ValueError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None
    return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}


def _bbox_area(box: Mapping[str, float]) -> float:
    return max(0.0, float(box["x2"]) - float(box["x1"])) * max(
        0.0, float(box["y2"]) - float(box["y1"])
    )


def _intersection_ratio(
    inner: Mapping[str, float], outer: Mapping[str, float]
) -> float:
    x1 = max(float(inner["x1"]), float(outer["x1"]))
    y1 = max(float(inner["y1"]), float(outer["y1"]))
    x2 = min(float(inner["x2"]), float(outer["x2"]))
    y2 = min(float(inner["y2"]), float(outer["y2"]))
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return ((x2 - x1) * (y2 - y1)) / max(1.0, _bbox_area(inner))


def _bbox_iou(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    x1 = max(float(left["x1"]), float(right["x1"]))
    y1 = max(float(left["y1"]), float(right["y1"]))
    x2 = min(float(left["x2"]), float(right["x2"]))
    y2 = min(float(left["y2"]), float(right["y2"]))
    if x2 <= x1 or y2 <= y1:
        return 0.0
    intersection = (x2 - x1) * (y2 - y1)
    left_area = (float(left["x2"]) - float(left["x1"])) * (
        float(left["y2"]) - float(left["y1"])
    )
    right_area = (float(right["x2"]) - float(right["x1"])) * (
        float(right["y2"]) - float(right["y1"])
    )
    return intersection / max(1.0, left_area + right_area - intersection)


def _center_distance_ratio(
    left: Mapping[str, float], right: Mapping[str, float]
) -> float:
    left_cx = (float(left["x1"]) + float(left["x2"])) / 2.0
    left_cy = (float(left["y1"]) + float(left["y2"])) / 2.0
    right_cx = (float(right["x1"]) + float(right["x2"])) / 2.0
    right_cy = (float(right["y1"]) + float(right["y2"])) / 2.0
    distance = float(np.hypot(left_cx - right_cx, left_cy - right_cy))
    left_diag = float(
        np.hypot(
            float(left["x2"]) - float(left["x1"]), float(left["y2"]) - float(left["y1"])
        )
    )
    right_diag = float(
        np.hypot(
            float(right["x2"]) - float(right["x1"]),
            float(right["y2"]) - float(right["y1"]),
        )
    )
    return distance / max(1.0, (left_diag + right_diag) / 2.0)


def _smooth_bbox(
    old: Mapping[str, float], new: Mapping[str, float], alpha: float
) -> dict[str, int]:
    old_weight = max(0.0, min(1.0, alpha))
    new_weight = 1.0 - old_weight
    return {
        key: int(round(float(old[key]) * old_weight + float(new[key]) * new_weight))
        for key in ("x1", "y1", "x2", "y2")
    }


def _raw_track_id(detection: Mapping[str, Any]) -> int | None:
    value = detection.get("track_id")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _display_group(object_type: str) -> str | None:
    if object_type == "PERSON":
        return "person"
    if object_type in {"VEHICLE", "MACHINERY", "FORKLIFT", "TRUCK"}:
        return "equipment"
    return None


def _person_ppe_region(person_box: Mapping[str, float], item: str) -> dict[str, float]:
    height = float(person_box["y2"]) - float(person_box["y1"])
    if item in {"helmet", "mask"}:
        return {
            "x1": float(person_box["x1"]),
            "y1": float(person_box["y1"]),
            "x2": float(person_box["x2"]),
            "y2": float(person_box["y1"]) + height * 0.42,
        }
    if item == "vest":
        return {
            "x1": float(person_box["x1"]),
            "y1": float(person_box["y1"]) + height * 0.20,
            "x2": float(person_box["x2"]),
            "y2": float(person_box["y1"]) + height * 0.78,
        }
    return dict(person_box)


def _person_ppe_badges(
    person: Mapping[str, Any], detections: Sequence[Mapping[str, Any]]
) -> list[str]:
    person_box = _bbox_from_detection(person)
    if person_box is None:
        return []

    by_item: dict[str, str] = {}
    for detection in detections:
        object_type = str(detection.get("object_type", "OBJECT")).upper()
        ppe = _PPE_BADGES.get(object_type)
        if ppe is None:
            continue
        item, badge = ppe
        ppe_box = _bbox_from_detection(detection)
        if ppe_box is None:
            continue
        region = _person_ppe_region(person_box, item)
        if _intersection_ratio(ppe_box, region) < 0.25:
            continue
        # Missing markers should win when a model emits both worn and missing candidates.
        if item not in by_item or badge.startswith("!"):
            by_item[item] = badge

    return [by_item[item] for item in _PPE_BADGE_ORDER if item in by_item]


@dataclass
class _DisplayTrack:
    group: str
    display_id: int
    raw_track_id: int | None
    bbox: dict[str, int]
    missed: int = 0


class DisplayStabilizer:
    """Display-only ID remapping and bbox smoothing for demo visualization."""

    def __init__(
        self,
        iou_threshold: float = 0.08,
        center_threshold: float = 0.45,
        smoothing: float = 0.70,
        max_missed: int = 15,
    ) -> None:
        self.iou_threshold = iou_threshold
        self.center_threshold = center_threshold
        self.smoothing = smoothing
        self.max_missed = max_missed
        self._next_display_id = {"person": 1, "equipment": 1}
        self._free_display_ids: dict[str, list[int]] = {"person": [], "equipment": []}
        self._tracks: dict[int, _DisplayTrack] = {}
        self._next_track_key = 1

    def _allocate_display_id(self, group: str) -> int:
        free_ids = self._free_display_ids.setdefault(group, [])
        if free_ids:
            return free_ids.pop(0)
        display_id = self._next_display_id.get(group, 1)
        self._next_display_id[group] = display_id + 1
        return display_id

    def _release_display_id(self, group: str, display_id: int) -> None:
        free_ids = self._free_display_ids.setdefault(group, [])
        if display_id <= 0 or display_id in free_ids:
            return
        free_ids.append(display_id)
        free_ids.sort()

    def _match_score(
        self, track_bbox: Mapping[str, float], bbox: Mapping[str, float]
    ) -> float:
        iou = _bbox_iou(track_bbox, bbox)
        if iou >= self.iou_threshold:
            return 1.0 + iou
        center_ratio = _center_distance_ratio(track_bbox, bbox)
        if center_ratio <= self.center_threshold:
            return 0.5 - center_ratio
        return -1.0

    def _find_track(
        self,
        group: str,
        raw_track_id: int | None,
        bbox: Mapping[str, float],
        unmatched: set[int],
    ) -> int | None:
        if raw_track_id is not None:
            for key in unmatched:
                track = self._tracks[key]
                if track.group == group and track.raw_track_id == raw_track_id:
                    return key

        best_key = None
        best_score = -1.0
        for key in unmatched:
            track = self._tracks[key]
            if track.group != group:
                continue
            score = self._match_score(track.bbox, bbox)
            if score > best_score:
                best_score = score
                best_key = key
        if best_score < 0.0:
            return None
        return best_key

    def update(self, detections: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        output = [dict(detection) for detection in detections]
        unmatched = set(self._tracks)

        for index, detection in enumerate(output):
            object_type = str(detection.get("object_type", "OBJECT")).upper()
            if object_type not in _TRACKABLE_DISPLAY_TYPES:
                continue
            group = _display_group(object_type)
            bbox = _bbox_from_detection(detection)
            if group is None or bbox is None:
                continue

            raw_id = _raw_track_id(detection)
            track_key = self._find_track(group, raw_id, bbox, unmatched)
            if track_key is None:
                track_key = self._next_track_key
                self._next_track_key += 1
                display_id = self._allocate_display_id(group)
                smoothed = {key: int(round(value)) for key, value in bbox.items()}
            else:
                track = self._tracks[track_key]
                display_id = track.display_id
                smoothed = _smooth_bbox(track.bbox, bbox, self.smoothing)
                unmatched.discard(track_key)

            output[index]["raw_track_id"] = raw_id
            output[index]["display_track_id"] = display_id
            output[index]["display_group"] = group
            output[index]["raw_bbox"] = dict(output[index]["bbox"])
            output[index]["bbox"] = smoothed
            self._tracks[track_key] = _DisplayTrack(
                group=group,
                display_id=display_id,
                raw_track_id=raw_id,
                bbox=smoothed,
                missed=0,
            )

        for key in list(unmatched):
            track = self._tracks[key]
            track.missed += 1
            if track.missed > self.max_missed:
                self._release_display_id(track.group, track.display_id)
                del self._tracks[key]

        return output


def _detection_color(detection: Mapping[str, Any]) -> tuple[int, int, int]:
    object_type = str(detection.get("object_type", "OBJECT")).upper()
    display_id = detection.get("display_track_id", detection.get("track_id"))
    if object_type in _TRACKABLE_DISPLAY_TYPES and display_id is not None:
        try:
            return _PALETTE[(int(display_id) - 1) % len(_PALETTE)]
        except (TypeError, ValueError):
            pass
    if object_type.startswith("NO_"):
        return (0, 80, 255)
    if object_type in {"HELMET", "VEST", "MASK", "GOGGLES", "GLOVES", "BOOTS"}:
        return (80, 220, 80)
    return (0, 255, 255)


def _compact_detection_label(
    detection: Mapping[str, Any],
    label_non_person: bool,
    person_badges: Sequence[str] = (),
) -> str:
    object_type = str(detection.get("object_type", "OBJECT")).upper()
    display_id = detection.get("display_track_id", detection.get("track_id"))
    if object_type == "PERSON":
        if display_id is not None:
            label = f"P{display_id}"
        else:
            label = "P"
        if person_badges:
            label = f"{label} {' '.join(person_badges)}"
        return label
    if object_type in {"VEHICLE", "MACHINERY", "FORKLIFT", "TRUCK"}:
        if display_id is not None:
            return f"E{display_id}"
        return "E"
    if not label_non_person:
        return ""
    return {
        "HELMET": "H",
        "VEST": "V",
        "SAFETY_VEST": "V",
        "MASK": "M",
        "NO_HELMET": "!H",
        "NO_VEST": "!V",
        "NO_MASK": "!M",
    }.get(object_type, "")


def draw_detections(
    frame: np.ndarray,
    detections: Sequence[Mapping[str, Any]],
    *,
    compact: bool = False,
    thickness: int = 2,
    font_scale: float = 0.5,
    label_non_person: bool = True,
) -> np.ndarray:
    annotated = frame.copy()
    height, width = annotated.shape[:2]
    person_badges_by_index: dict[int, list[str]] = {}
    if compact:
        for index, detection in enumerate(detections):
            if str(detection.get("object_type", "OBJECT")).upper() == "PERSON":
                person_badges_by_index[index] = _person_ppe_badges(
                    detection, detections
                )

    for index, detection in enumerate(detections):
        if detection.get("suppress_detection"):
            continue
        bbox = detection.get("bbox", {})
        try:
            x1 = max(0, min(width - 1, int(bbox.get("x1", 0))))
            y1 = max(0, min(height - 1, int(bbox.get("y1", 0))))
            x2 = max(0, min(width - 1, int(bbox.get("x2", 0))))
            y2 = max(0, min(height - 1, int(bbox.get("y2", 0))))
        except (AttributeError, TypeError, ValueError):
            continue

        if x2 <= x1 or y2 <= y1:
            continue

        label = (
            _compact_detection_label(
                detection,
                label_non_person,
                person_badges_by_index.get(index, []),
            )
            if compact
            else format_detection_label(detection)
        )
        color = _detection_color(detection) if compact else (0, 255, 0)

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, max(1, thickness))
        if label:
            label_y = max(14, y1 - 6)
            text_size, _ = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
            )
            cv2.rectangle(
                annotated,
                (x1, max(0, label_y - text_size[1] - 4)),
                (min(width - 1, x1 + text_size[0] + 4), min(height - 1, label_y + 2)),
                color,
                -1,
            )
            cv2.putText(
                annotated,
                label,
                (x1 + 2, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

    return annotated


def draw_quadrant_overlay(frame: np.ndarray, quadrants: Sequence[int]) -> np.ndarray:
    annotated = frame.copy()
    height, width = annotated.shape[:2]
    center_x = width // 2
    center_y = height // 2

    overlay = annotated.copy()
    for quadrant in quadrants:
        if quadrant == 1:
            x1, y1, x2, y2 = center_x, 0, width, center_y
        elif quadrant == 2:
            x1, y1, x2, y2 = 0, 0, center_x, center_y
        elif quadrant == 3:
            x1, y1, x2, y2 = 0, center_y, center_x, height
        elif quadrant == 4:
            x1, y1, x2, y2 = center_x, center_y, width, height
        else:
            continue
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), -1)

    annotated = cv2.addWeighted(overlay, 0.18, annotated, 0.82, 0)
    cv2.line(annotated, (center_x, 0), (center_x, height), (255, 255, 255), 1)
    cv2.line(annotated, (0, center_y), (width, center_y), (255, 255, 255), 1)
    cv2.putText(
        annotated,
        "(0,0)",
        (center_x + 6, center_y - 6),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (255, 255, 255),
        1,
    )
    cv2.putText(
        annotated,
        "Q1",
        (width - 36, 22),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
    )
    cv2.putText(
        annotated, "Q2", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1
    )
    cv2.putText(
        annotated,
        "Q3",
        (8, height - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
    )
    cv2.putText(
        annotated,
        "Q4",
        (width - 36, height - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
    )
    return annotated


def _zone_value(zone: Any, key: str, default: Any = None) -> Any:
    if isinstance(zone, Mapping):
        return zone.get(key, default)
    return getattr(zone, key, default)


def _zone_label(zone: Any) -> str:
    return str(_zone_value(zone, "name") or _zone_value(zone, "zone_id", "zone"))


def _quadrant_polygon(width: int, height: int, quadrant: int) -> list[tuple[int, int]]:
    center_x = width // 2
    center_y = height // 2
    if quadrant == 1:
        return [(center_x, 0), (width, 0), (width, center_y), (center_x, center_y)]
    if quadrant == 2:
        return [(0, 0), (center_x, 0), (center_x, center_y), (0, center_y)]
    if quadrant == 3:
        return [(0, center_y), (center_x, center_y), (center_x, height), (0, height)]
    if quadrant == 4:
        return [
            (center_x, center_y),
            (width, center_y),
            (width, height),
            (center_x, height),
        ]
    return []


def _parse_zone_points(zone: Any, width: int, height: int) -> list[tuple[int, int]]:
    zone_type = str(
        _zone_value(zone, "type", _zone_value(zone, "zone_type", ""))
    ).lower()
    if zone_type == "quadrant":
        return _quadrant_polygon(
            width, height, int(_zone_value(zone, "quadrant", 0) or 0)
        )

    points_norm = _zone_value(zone, "points_norm", ()) or ()
    if points_norm:
        points: list[tuple[int, int]] = []
        for point in points_norm:
            if isinstance(point, Mapping):
                x = float(point.get("x", 0.0))
                y = float(point.get("y", 0.0))
            else:
                x, y = point
            points.append((int(round(x * width)), int(round(y * height))))
        return points

    raw_points = _zone_value(zone, "points", ()) or ()
    points = []
    for point in raw_points:
        if isinstance(point, Mapping):
            x = float(point.get("x", 0.0))
            y = float(point.get("y", 0.0))
        else:
            x, y = point
        points.append((int(round(x)), int(round(y))))
    return points


def draw_zone_overlay(frame: np.ndarray, zones: Sequence[Any]) -> np.ndarray:
    annotated = frame.copy()
    if not zones:
        return annotated

    height, width = annotated.shape[:2]
    overlay = annotated.copy()
    for zone in zones:
        points = _parse_zone_points(zone, width, height)
        if len(points) < 3:
            continue

        polygon = np.array(points, dtype=np.int32)
        color = (0, 165, 255)
        cv2.fillPoly(overlay, [polygon], color)
        cv2.polylines(annotated, [polygon], isClosed=True, color=color, thickness=2)

        label_x = max(0, min(width - 1, min(x for x, _ in points)))
        label_y = max(18, min(height - 1, min(y for _, y in points) - 8))
        cv2.putText(
            annotated,
            _zone_label(zone),
            (label_x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

    return cv2.addWeighted(overlay, 0.18, annotated, 0.82, 0)
