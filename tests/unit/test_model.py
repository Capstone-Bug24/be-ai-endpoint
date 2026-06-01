from __future__ import annotations

import numpy as np

from capruntime.model import MockModelRunner, OnnxModelRunner, normalize_object_type


def test_mock_model_produces_detection() -> None:
    frame = np.zeros((120, 200, 3), dtype=np.uint8)
    runner = MockModelRunner(score_threshold=0.2)
    detections = runner.infer(frame, frame_index=3)
    assert len(detections) == 1
    det = detections[0]
    assert det["event_type"] == "DETECTION"
    assert det["confidence"] >= 0.2


def test_onnx_model_returns_empty_by_baseline() -> None:
    frame = np.zeros((120, 200, 3), dtype=np.uint8)
    runner = OnnxModelRunner(model_path="dummy.onnx")
    assert runner.infer(frame, frame_index=0) == []


def test_normalize_object_type_maps_ppe_labels() -> None:
    assert normalize_object_type("Person") == "PERSON"
    assert normalize_object_type("Hardhat") == "HELMET"
    assert normalize_object_type("Safety Vest") == "VEST"
    assert normalize_object_type("NO-Hardhat") == "NO_HELMET"
    assert normalize_object_type("No Safety Vest") == "NO_VEST"
