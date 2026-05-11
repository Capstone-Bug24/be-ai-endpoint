from __future__ import annotations

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


def build_video_writer(output_path: str | Path, frame_size: tuple[int, int], fps: float) -> cv2.VideoWriter:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*("XVID" if path.suffix.lower() == ".avi" else "mp4v"))
    writer = cv2.VideoWriter(str(path), fourcc, fps, frame_size)
    if not writer.isOpened():
        raise RuntimeError(f"Unable to open output video writer: {path}")
    return writer


def draw_detections(frame: np.ndarray, detections: Sequence[Mapping[str, Any]]) -> np.ndarray:
    annotated = frame.copy()
    height, width = annotated.shape[:2]

    for detection in detections:
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

        label = format_detection_label(detection)
        color = (0, 255, 0)

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        if label:
            label_y = max(18, y1 - 8)
            cv2.putText(
                annotated,
                label,
                (x1, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
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
    cv2.putText(annotated, "(0,0)", (center_x + 6, center_y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    cv2.putText(annotated, "Q1", (width - 36, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.putText(annotated, "Q2", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.putText(annotated, "Q3", (8, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.putText(annotated, "Q4", (width - 36, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return annotated
