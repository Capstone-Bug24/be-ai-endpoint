from __future__ import annotations

import numpy as np

from capruntime.visualization import (
    DisplayStabilizer,
    draw_detections,
    draw_quadrant_overlay,
    format_detection_label,
    resolve_video_fps,
)


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


def test_display_stabilizer_remaps_large_raw_person_ids() -> None:
    stabilizer = DisplayStabilizer()

    detections = stabilizer.update(
        [
            {
                "object_type": "PERSON",
                "track_id": 2306,
                "bbox": {"x1": 10, "y1": 10, "x2": 40, "y2": 70},
            },
            {
                "object_type": "HELMET",
                "track_id": 2307,
                "bbox": {"x1": 18, "y1": 10, "x2": 30, "y2": 24},
            },
        ]
    )

    assert detections[0]["display_track_id"] == 1
    assert detections[0]["raw_track_id"] == 2306
    assert "display_track_id" not in detections[1]


def test_display_stabilizer_keeps_display_id_when_raw_id_changes_nearby() -> None:
    stabilizer = DisplayStabilizer()

    first = stabilizer.update(
        [
            {
                "object_type": "PERSON",
                "track_id": 2306,
                "bbox": {"x1": 10, "y1": 10, "x2": 40, "y2": 70},
            }
        ]
    )
    second = stabilizer.update(
        [
            {
                "object_type": "PERSON",
                "track_id": 2401,
                "bbox": {"x1": 12, "y1": 11, "x2": 42, "y2": 71},
            }
        ]
    )

    assert first[0]["display_track_id"] == 1
    assert second[0]["display_track_id"] == 1


def test_compact_draw_attaches_ppe_badges_to_person_label() -> None:
    frame = np.zeros((90, 90, 3), dtype=np.uint8)
    detections = [
        {
            "object_type": "PERSON",
            "track_id": 1,
            "bbox": {"x1": 10, "y1": 10, "x2": 50, "y2": 80},
        },
        {
            "object_type": "HELMET",
            "bbox": {"x1": 22, "y1": 12, "x2": 38, "y2": 28},
        },
        {
            "object_type": "NO_VEST",
            "bbox": {"x1": 20, "y1": 35, "x2": 43, "y2": 68},
        },
    ]

    annotated = draw_detections(frame, detections, compact=True, label_non_person=False)

    assert annotated is not frame
    assert int(annotated.sum()) > 0
