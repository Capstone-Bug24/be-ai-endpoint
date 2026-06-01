#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from capruntime.emitter import ResilientEmitter  # noqa: E402
from capruntime.events import build_analysis_result  # noqa: E402
from capruntime.model import create_model_runner  # noqa: E402
from capruntime.rules import apply_runtime_rules  # noqa: E402
from capruntime.runtime import _zone_definitions  # noqa: E402
from capruntime.sensors import SensorHub  # noqa: E402
from capruntime.settings import load_runtime_settings  # noqa: E402
from capruntime.video import create_video_source  # noqa: E402
from capruntime.visualization import (  # noqa: E402
    DisplayStabilizer,
    build_video_writer,
    draw_detections,
    draw_zone_overlay,
    resolve_video_fps,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Live webcam/RTSP visualization with runtime rules"
    )
    parser.add_argument("--config", default="configs/runtime.yaml")
    parser.add_argument(
        "--source-type", choices=("webcam", "rtsp", "file"), default="webcam"
    )
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--rtsp-url", default=None)
    parser.add_argument("--video", default=None)
    parser.add_argument("--loop", action="store_true", help="loop file source")
    parser.add_argument("--model-type", choices=("mock", "yolo", "onnx"), default=None)
    parser.add_argument("--yolo-model-path", default=None)
    parser.add_argument(
        "--device", default=None, help="YOLO device override, e.g. cpu, cuda:0, 0"
    )
    tracking_group = parser.add_mutually_exclusive_group()
    tracking_group.add_argument(
        "--tracking", dest="tracking", action="store_true", default=None
    )
    tracking_group.add_argument("--no-tracking", dest="tracking", action="store_false")
    parser.add_argument(
        "--tracker", default=None, help="Ultralytics tracker yaml, e.g. bytetrack.yaml"
    )
    parser.add_argument("--score-threshold", type=float, default=None)
    parser.add_argument("--backend-url", default=None)
    parser.add_argument(
        "--emit",
        action="store_true",
        help="send events to backend; default only writes optional JSONL",
    )
    parser.add_argument("--output-jsonl", default=None)
    parser.add_argument("--output-video", default=None)
    parser.add_argument(
        "--resize-width",
        type=int,
        default=None,
        help="resize frames before inference/display; boxes are reported in resized-frame coordinates",
    )
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument(
        "--no-window", action="store_true", help="do not open a cv2 window"
    )
    return parser.parse_args()


def _resize_frame(frame, width: int | None):
    if width is None or width <= 0:
        return frame
    height, current_width = frame.shape[:2]
    if current_width == width:
        return frame
    scale = width / float(current_width)
    return cv2.resize(frame, (width, max(1, int(height * scale))))


def _build_cli_overrides(args: argparse.Namespace) -> dict:
    source_cfg: dict[str, object] = {"type": args.source_type}
    runtime_cfg: dict[str, object] = {}
    model_cfg: dict[str, object] = {}
    backend_cfg: dict[str, object] = {}

    if args.source_type == "webcam":
        source_cfg["webcam_index"] = args.camera_index
    if args.source_type == "rtsp" and args.rtsp_url is not None:
        source_cfg["rtsp_url"] = args.rtsp_url
    if args.source_type == "file" and args.video is not None:
        source_cfg["file_path"] = str(Path(args.video).expanduser())
    if args.loop:
        source_cfg["loop"] = True
    if args.output_jsonl is not None:
        runtime_cfg["output_jsonl"] = args.output_jsonl
    if args.model_type is not None:
        model_cfg["type"] = args.model_type
    if args.yolo_model_path is not None:
        model_cfg["yolo_model_path"] = args.yolo_model_path
    if args.device is not None:
        model_cfg["device"] = args.device
    if args.tracking is not None:
        model_cfg["tracking"] = args.tracking
    if args.tracker is not None:
        model_cfg["tracker"] = args.tracker
    if args.score_threshold is not None:
        model_cfg["score_threshold"] = args.score_threshold
    if args.backend_url is not None:
        backend_cfg["url"] = args.backend_url

    overrides: dict[str, dict[str, object]] = {"source": source_cfg}
    if runtime_cfg:
        overrides["runtime"] = runtime_cfg
    if model_cfg:
        overrides["model"] = model_cfg
    if backend_cfg:
        overrides["backend"] = backend_cfg
    return overrides


def main() -> int:
    args = _parse_args()
    settings = load_runtime_settings(
        config_path=args.config,
        cli_overrides=_build_cli_overrides(args),
    )
    source = create_video_source(settings.source)
    model_runner = create_model_runner(settings.model)
    sensor_hub = SensorHub(settings.sensors)
    emitter = ResilientEmitter(
        backend=settings.backend,
        spool=settings.spool,
        dry_run=not args.emit,
        output_jsonl=settings.output_jsonl,
    )
    writer = None
    frame_index = 0
    emitted = 0
    display_stabilizer = DisplayStabilizer()
    sensor_hub.start()
    try:
        while True:
            ok, frame = source.read()
            if not ok or frame is None:
                if source.is_live:
                    continue
                break
            frame_ts = _now_iso()
            source_frame_ts, frame_ts_source = source.frame_timestamp()
            frame_ts = source_frame_ts or frame_ts
            frame_ts_source = frame_ts_source or "ai_read_time"
            frame = _resize_frame(frame, args.resize_width)

            detections = model_runner.infer(frame, frame_index)
            sensors = sensor_hub.snapshot()
            detections = apply_runtime_rules(
                detections=detections,
                frame=frame,
                sensor_snapshot=sensors,
                danger_zones=settings.danger_zones,
                sensor_rules=settings.sensor_rules,
                ppe_rules=settings.ppe_rules,
            )

            if detections:
                analysis = build_analysis_result(
                    site_id=settings.site_id,
                    camera_id=settings.camera_id,
                    detections=detections,
                    sensor_snapshot=sensors,
                    frame_id=frame_index,
                    frame_ts=frame_ts,
                    frame_ts_source=frame_ts_source,
                    frame_shape=frame.shape,
                    zone_definitions=_zone_definitions(settings),
                )
                emitter.emit(analysis)
                emitted += 1

            annotated = draw_zone_overlay(frame, settings.danger_zones)
            annotated = draw_detections(
                annotated,
                display_stabilizer.update(detections),
                compact=True,
                thickness=1,
                font_scale=0.38,
                label_non_person=False,
            )

            if writer is None and args.output_video:
                height, width = annotated.shape[:2]
                writer = build_video_writer(
                    args.output_video,
                    (width, height),
                    resolve_video_fps(0.0, default_fps=float(settings.fps_limit or 10)),
                )
            if writer is not None:
                writer.write(annotated)

            if not args.no_window:
                cv2.imshow("capruntime live inference", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            frame_index += 1
            if args.max_frames is not None and frame_index >= args.max_frames:
                break
    finally:
        sensor_hub.stop()
        source.release()
        emitter.close()
        if writer is not None:
            writer.release()
        if not args.no_window:
            cv2.destroyAllWindows()

    print(
        f"frames={frame_index} events={emitted} "
        f"backend_emit={args.emit} spool_pending={emitter.pending_spool_size}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
