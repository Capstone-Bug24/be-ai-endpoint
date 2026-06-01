from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Protocol

import numpy as np

from .settings import ModelSettings


class ModelRunner(Protocol):
    def infer(self, frame: np.ndarray, frame_index: int) -> list[dict]: ...


_OBJECT_TYPE_ALIASES = {
    "person": "PERSON",
    "worker": "PERSON",
    "human": "PERSON",
    "hardhat": "HELMET",
    "hard_hat": "HELMET",
    "helmet": "HELMET",
    "safetyhelmet": "HELMET",
    "safety_helmet": "HELMET",
    "nohardhat": "NO_HELMET",
    "no_hardhat": "NO_HELMET",
    "no_hard_hat": "NO_HELMET",
    "nohelmet": "NO_HELMET",
    "no_helmet": "NO_HELMET",
    "no_safety_helmet": "NO_HELMET",
    "safetyvest": "VEST",
    "safety_vest": "VEST",
    "vest": "VEST",
    "novest": "NO_VEST",
    "no_vest": "NO_VEST",
    "no_safety_vest": "NO_VEST",
    "mask": "MASK",
    "nomask": "NO_MASK",
    "no_mask": "NO_MASK",
    "goggles": "GOGGLES",
    "goggle": "GOGGLES",
    "nogoggles": "NO_GOGGLES",
    "no_goggles": "NO_GOGGLES",
    "gloves": "GLOVES",
    "glove": "GLOVES",
    "nogloves": "NO_GLOVES",
    "no_gloves": "NO_GLOVES",
    "boots": "BOOTS",
    "boot": "BOOTS",
    "noboots": "NO_BOOTS",
    "no_boots": "NO_BOOTS",
}

_TRACKABLE_OBJECT_TYPES = {
    "PERSON",
    "VEHICLE",
    "MACHINERY",
    "FORKLIFT",
    "TRUCK",
}


def normalize_object_type(label: str) -> str:
    text = str(label or "OBJECT").strip()
    if not text:
        return "OBJECT"
    compact = text.lower().replace("-", "_").replace(" ", "_")
    compact = "_".join(part for part in compact.split("_") if part)
    return _OBJECT_TYPE_ALIASES.get(
        compact, text.upper().replace(" ", "_").replace("-", "_")
    )


def _ensure_ultralytics_config_dir() -> None:
    config_dir = os.environ.get("YOLO_CONFIG_DIR")
    if not config_dir:
        base_dir = os.environ.get("CAPRUNTIME_TMP")
        if not base_dir:
            base_dir = r"C:\tmp" if os.name == "nt" else "/tmp"
        config_dir = str(Path(base_dir) / "ultralytics")
        os.environ["YOLO_CONFIG_DIR"] = config_dir
    Path(config_dir).mkdir(parents=True, exist_ok=True)


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
                "event_type": "DETECTION",
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
    device: str | None = None
    tracking: bool = False
    tracker: str = "bytetrack.yaml"

    def __post_init__(self) -> None:
        try:
            _ensure_ultralytics_config_dir()
            from ultralytics import YOLO  # type: ignore
        except Exception as exc:
            raise ImportError(
                "ultralytics is required for model.type=yolo. Install requirements-model.txt."
            ) from exc
        self._model = YOLO(self.model_path)

    def infer(self, frame: np.ndarray, frame_index: int) -> list[dict]:
        predict_kwargs = {"conf": self.score_threshold, "verbose": False}
        if self.device:
            predict_kwargs["device"] = self.device
        if self.tracking:
            results = self._model.track(
                frame,
                persist=True,
                tracker=self.tracker,
                **predict_kwargs,
            )
        else:
            results = self._model.predict(frame, **predict_kwargs)
        payloads: list[dict] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()
                raw_label = str(result.names.get(cls_id, "OBJECT"))
                label = normalize_object_type(raw_label)
                track_id = None
                box_id = getattr(box, "id", None)
                if label in _TRACKABLE_OBJECT_TYPES and box_id is not None:
                    try:
                        track_id = int(box_id[0])
                    except (TypeError, ValueError, IndexError):
                        track_id = None
                payloads.append(
                    {
                        "event_type": "DETECTION",
                        "object_type": label,
                        "model_label": raw_label,
                        "severity": "MEDIUM",
                        "confidence": conf,
                        "bbox": {
                            "x1": int(xyxy[0]),
                            "y1": int(xyxy[1]),
                            "x2": int(xyxy[2]),
                            "y2": int(xyxy[3]),
                        },
                        "track_id": track_id,
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
            device=model.device,
            tracking=model.tracking,
            tracker=model.tracker,
        )
    if model.type == "onnx":
        return OnnxModelRunner(
            model_path=model.onnx_model_path,
            score_threshold=model.score_threshold,
        )
    raise ValueError(f"Unsupported model type: {model.type}")
