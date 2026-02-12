from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

from .runtime import CameraRuntime
from .settings import load_runtime_settings


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capstone runtime v2")
    parser.add_argument("--config", default="configs/runtime.yaml", help="runtime config yaml")
    parser.add_argument("--camera-id", default=None)
    parser.add_argument("--site-id", default=None)

    parser.add_argument("--source-type", choices=("file", "rtsp", "webcam"), default=None)
    parser.add_argument("--rtsp-url", default=None)
    parser.add_argument("--video", default=None, help="file source path override")
    parser.add_argument("--camera-index", type=int, default=None)
    parser.add_argument("--loop", action="store_true", help="loop file source")

    parser.add_argument("--model-type", choices=("mock", "yolo", "onnx"), default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-jsonl", default=None)
    parser.add_argument("--backend-url", default=None)
    parser.add_argument("--fps-limit", type=int, default=None)
    parser.add_argument("--max-events", type=int, default=None)
    return parser.parse_args()


def _build_cli_overrides(args: argparse.Namespace) -> dict[str, Any]:
    runtime_cfg: dict[str, Any] = {}
    source_cfg: dict[str, Any] = {}
    model_cfg: dict[str, Any] = {}
    backend_cfg: dict[str, Any] = {}

    if args.camera_id is not None:
        runtime_cfg["camera_id"] = args.camera_id
    if args.site_id is not None:
        runtime_cfg["site_id"] = args.site_id
    if args.output_jsonl is not None:
        runtime_cfg["output_jsonl"] = args.output_jsonl
    if args.fps_limit is not None:
        runtime_cfg["fps_limit"] = args.fps_limit
    if args.max_events is not None:
        runtime_cfg["max_events"] = args.max_events
    if args.dry_run:
        runtime_cfg["dry_run"] = True

    if args.source_type is not None:
        source_cfg["type"] = args.source_type
    if args.rtsp_url is not None:
        source_cfg["rtsp_url"] = args.rtsp_url
    if args.video is not None:
        source_cfg["file_path"] = str(Path(args.video).expanduser())
    if args.camera_index is not None:
        source_cfg["webcam_index"] = args.camera_index
    if args.loop:
        source_cfg["loop"] = True

    if args.model_type is not None:
        model_cfg["type"] = args.model_type

    if args.backend_url is not None:
        backend_cfg["url"] = args.backend_url

    merged: dict[str, Any] = {}
    if runtime_cfg:
        merged["runtime"] = runtime_cfg
    if source_cfg:
        merged["source"] = source_cfg
    if model_cfg:
        merged["model"] = model_cfg
    if backend_cfg:
        merged["backend"] = backend_cfg
    return merged


def main() -> int:
    _setup_logging()
    args = _parse_args()
    settings = load_runtime_settings(
        config_path=args.config,
        cli_overrides=_build_cli_overrides(args),
    )
    runtime = CameraRuntime(settings)
    emitted = runtime.run()
    logging.getLogger(__name__).info("completed emitted=%d", emitted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
