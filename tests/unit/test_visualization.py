from __future__ import annotations

import numpy as np

from capruntime.visualization import draw_detections, draw_quadrant_overlay, format_detection_label, resolve_video_fps


def test_format_detection_label_rounds_confidence() -> None:
    label = format_detection_label({"object_type": "PERSON", "confidence": 0.756})
    assert label == "PERSON 0.76"


def test_format_detection_label_includes_event_context() -> None:
    label = format_detection_label(
        {
            "object_type": "PERSON",
            "confidence": 0.756,
            "event_type": "ZONE_INTRUSION",
            "severity": "HIGH",
            "zones": [
                {"zone_id": "danger_q2", "inside": True},
                {"zone_id": "forklift_lane", "inside": True},
            ],
        }
    )
    assert label == "PERSON 0.76 ZONE_INTRUSION HIGH danger_q2,forklift_lane"


def test_resolve_video_fps_uses_default_for_invalid_values() -> None:
    assert resolve_video_fps(0.0) == 10.0
    assert resolve_video_fps(float("nan")) == 10.0
    assert resolve_video_fps(12.5) == 12.5


def test_draw_detections_returns_annotated_copy() -> None:
    frame = np.zeros((80, 80, 3), dtype=np.uint8)

    annotated = draw_detections(
        frame,
        [
            {
                "object_type": "PERSON",
                "confidence": 0.9,
                "bbox": {"x1": 10, "y1": 10, "x2": 40, "y2": 50},
            }
        ],
    )

    assert annotated is not frame
    assert int(frame.sum()) == 0
    assert int(annotated.sum()) > 0


def test_draw_quadrant_overlay_marks_frame() -> None:
    frame = np.zeros((80, 80, 3), dtype=np.uint8)

    annotated = draw_quadrant_overlay(frame, [1])

    assert annotated is not frame
    assert int(annotated.sum()) > 0
