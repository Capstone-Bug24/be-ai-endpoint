from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .settings import ModelSettings


class ModelRunner(Protocol):
    def infer(self, frame: np.ndarray, frame_index: int) -> list[dict]:
        ...


@dataclass
class MockModelRunner:
    score_threshold: float = 0.25

    def infer(self, frame: np.ndarray, frame_index: int) -> list[dict]:
        if frame is None:
            return []
        h, w = frame.shape[:2]
        box_w = max(20, w // 6)
        box_h = max(20, h // 4)
        x1 = (frame_index * 7) % max(1, w - box_w)
        y1 = (frame_index * 5) % max(1, h - box_h)
        return [
            {
                "event_type": "ZONE_INTRUSION",
                "object_type": "PERSON",
                "severity": "LOW",
                "confidence": max(self.score_threshold, 0.75),
                "bbox": {
                    "x1": int(x1),
                    "y1": int(y1),
                    "x2": int(x1 + box_w),
                    "y2": int(y1 + box_h),
                },
                "track_id": frame_index,
            }
        ]


@dataclass
class YoloModelRunner:
    model_path: str
    score_threshold: float = 0.25

    def __post_init__(self) -> None:
        try:
            from ultralytics import YOLO  # type: ignore
        except Exception as exc:
            raise ImportError(
                "ultralytics is required for model.type=yolo. Install requirements-model.txt."
            ) from exc
        self._model = YOLO(self.model_path)

    def infer(self, frame: np.ndarray, frame_index: int) -> list[dict]:
        results = self._model.predict(frame, conf=self.score_threshold, verbose=False)
        payloads: list[dict] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                label = str(result.names.get(cls_id, "OBJECT")).upper()
                payloads.append(
                    {
                        "event_type": "DETECTION",
                        "object_type": label,
                        "severity": "MEDIUM",
                        "confidence": conf,
                        "bbox": {
                            "x1": int(xyxy[0]),
                            "y1": int(xyxy[1]),
                            "x2": int(xyxy[2]),
                            "y2": int(xyxy[3]),
                        },
                        "track_id": None,
                    }
                )
        return payloads


@dataclass
class OnnxModelRunner:
    model_path: str | None = None
    score_threshold: float = 0.25

    def infer(self, frame: np.ndarray, frame_index: int) -> list[dict]:
        # Capstone baseline keeps ONNX path simple.
        # If ONNX is selected without custom decode logic, return empty detections.
        _ = frame
        _ = frame_index
        _ = self.model_path
        _ = self.score_threshold
        return []


def create_model_runner(model: ModelSettings) -> ModelRunner:
    if model.type == "mock":
        return MockModelRunner(score_threshold=model.score_threshold)
    if model.type == "yolo":
        if not model.yolo_model_path:
            raise ValueError("model.yolo_model_path is required when model.type=yolo")
        return YoloModelRunner(
            model_path=model.yolo_model_path,
            score_threshold=model.score_threshold,
        )
    if model.type == "onnx":
        return OnnxModelRunner(
            model_path=model.onnx_model_path,
            score_threshold=model.score_threshold,
        )
    raise ValueError(f"Unsupported model type: {model.type}")
