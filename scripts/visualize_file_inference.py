#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from capruntime.model import create_model_runner  # noqa: E402
from capruntime.settings import load_runtime_settings  # noqa: E402
from capruntime.visualization import (  # noqa: E402
    build_video_writer,
    draw_detections,
    resolve_video_fps,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render model detections onto a local video file"
    )
    parser.add_argument("--config", default="configs/runtime.yaml")
    parser.add_argument("--video", default=None, help="file source path override")
    parser.add_argument("--output-video", default="outputs/annotated.mp4")
    parser.add_argument("--model-type", choices=("mock", "yolo", "onnx"), default=None)
    parser.add_argument("--score-threshold", type=float, default=None)
    parser.add_argument("--yolo-model-path", default=None)
    parser.add_argument("--onnx-model-path", default=None)
    parser.add_argument("--max-frames", type=int, default=None)
    return parser.parse_args()


def _build_cli_overrides(args: argparse.Namespace) -> dict:
    source_cfg: dict[str, object] = {"type": "file"}
    model_cfg: dict[str, object] = {}

    if args.video is not None:
        source_cfg["file_path"] = str(Path(args.video).expanduser())
    if args.model_type is not None:
        model_cfg["type"] = args.model_type
    if args.score_threshold is not None:
        model_cfg["score_threshold"] = args.score_threshold
    if args.yolo_model_path is not None:
        model_cfg["yolo_model_path"] = args.yolo_model_path
    if args.onnx_model_path is not None:
        model_cfg["onnx_model_path"] = args.onnx_model_path

    overrides = {"source": source_cfg}
    if model_cfg:
        overrides["model"] = model_cfg
    return overrides


def main() -> int:
    args = _parse_args()
    settings = load_runtime_settings(
        config_path=args.config,
        cli_overrides=_build_cli_overrides(args),
    )
    if settings.source.type != "file" or not settings.source.file_path:
        raise ValueError("visualization helper requires a file video source")

    capture = cv2.VideoCapture(str(settings.source.file_path))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video file: {settings.source.file_path}")

    model_runner = create_model_runner(settings.model)
    writer = None
    frames_written = 0
    detections_drawn = 0
    frame_index = 0

    try:
        fps = resolve_video_fps(
            capture.get(cv2.CAP_PROP_FPS), default_fps=float(settings.fps_limit or 10)
        )
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                break

            if writer is None:
                height, width = frame.shape[:2]
                writer = build_video_writer(args.output_video, (width, height), fps)

            detections = model_runner.infer(frame, frame_index)
            detections_drawn += len(detections)
            writer.write(draw_detections(frame, detections))
            frames_written += 1
            frame_index += 1

            if args.max_frames is not None and frames_written >= args.max_frames:
                break
    finally:
        capture.release()
        if writer is not None:
            writer.release()

    if frames_written == 0:
        raise RuntimeError("No frames were written; input video may be empty")

    print(
        f"annotated_video={args.output_video} frames_written={frames_written} detections_drawn={detections_drawn}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
