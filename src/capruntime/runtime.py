from __future__ import annotations


from datetime import datetime, timezone

import logging

import time


from .emitter import ResilientEmitter

from .events import build_analysis_result

from .model import ModelRunner, create_model_runner

from .rules import apply_runtime_rules

from .sensors import SensorHub

from .settings import RuntimeSettings

from .video import VideoSource, create_video_source


logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _quadrant_points_norm(quadrant: int) -> list[dict[str, float]]:
    if quadrant == 1:
        return [
            {"x": 0.5, "y": 0.0},
            {"x": 1.0, "y": 0.0},
            {"x": 1.0, "y": 0.5},
            {"x": 0.5, "y": 0.5},
        ]
    if quadrant == 2:
        return [
            {"x": 0.0, "y": 0.0},
            {"x": 0.5, "y": 0.0},
            {"x": 0.5, "y": 0.5},
            {"x": 0.0, "y": 0.5},
        ]
    if quadrant == 3:
        return [
            {"x": 0.0, "y": 0.5},
            {"x": 0.5, "y": 0.5},
            {"x": 0.5, "y": 1.0},
            {"x": 0.0, "y": 1.0},
        ]
    if quadrant == 4:
        return [
            {"x": 0.5, "y": 0.5},
            {"x": 1.0, "y": 0.5},
            {"x": 1.0, "y": 1.0},
            {"x": 0.5, "y": 1.0},
        ]
    return []


def _points_payload(points: tuple[tuple[float, float], ...]) -> list[dict[str, float]]:
    return [{"x": float(x), "y": float(y)} for x, y in points]


def _zone_definitions(settings: RuntimeSettings) -> list[dict[str, object]]:
    zones: list[dict[str, object]] = []
    for zone in settings.danger_zones:
        payload: dict[str, object] = {
            "zone_id": zone.zone_id,
            "zone_type": zone.type,
            "severity": zone.severity,
            "basis": zone.basis,
            "min_overlap_ratio": zone.min_overlap_ratio,
            "foot_band_ratio": zone.foot_band_ratio,
            "points_norm": _quadrant_points_norm(zone.quadrant)
            if zone.type == "quadrant"
            else _points_payload(zone.points_norm),
        }
        if zone.name:
            payload["name"] = zone.name
        if zone.type == "quadrant":
            payload["quadrant"] = zone.quadrant
        if zone.points:
            payload["points"] = _points_payload(zone.points)
        zones.append(payload)
    return zones


class CameraRuntime:
    """Single-process runtime: one camera + many sensors."""

    def __init__(
        self,
        settings: RuntimeSettings,
        source: VideoSource | None = None,
        model_runner: ModelRunner | None = None,
        sensor_hub: SensorHub | None = None,
        emitter: ResilientEmitter | None = None,
    ) -> None:
        self.settings = settings

        self.source = source or create_video_source(settings.source)

        self.model_runner = model_runner or create_model_runner(settings.model)

        self.sensor_hub = sensor_hub or SensorHub(settings.sensors)

        self.emitter = emitter or ResilientEmitter(
            backend=settings.backend,
            spool=settings.spool,
            dry_run=settings.dry_run,
            output_jsonl=settings.output_jsonl,
        )

    def run(self) -> int:
        emitted = 0

        frame_index = 0

        period = (
            0.0
            if self.settings.fps_limit <= 0
            else 1.0 / float(self.settings.fps_limit)
        )

        next_tick = 0.0

        stop_after = self.settings.max_events

        logger.info(
            "runtime start camera=%s source=%s model=%s sensors=%d dry_run=%s",
            self.settings.camera_id,
            self.settings.source.type,
            self.settings.model.type,
            len(self.settings.sensors),
            self.settings.dry_run,
        )

        self.sensor_hub.start()

        try:
            while True:
                if period > 0.0:
                    now = time.monotonic()

                    if now < next_tick:
                        time.sleep(next_tick - now)

                    next_tick = time.monotonic() + period

                ok, frame = self.source.read()

                if not ok or frame is None:
                    if self.source.is_live:
                        time.sleep(0.05)

                        continue

                    break

                frame_read_ts = _now_iso()
                source_frame_ts, frame_ts_source = self.source.frame_timestamp()
                frame_ts = source_frame_ts or frame_read_ts
                frame_ts_source = frame_ts_source or "ai_read_time"

                detections = self.model_runner.infer(frame, frame_index)

                sensors = self.sensor_hub.snapshot()

                detections = apply_runtime_rules(
                    detections=detections,
                    frame=frame,
                    sensor_snapshot=sensors,
                    danger_zones=self.settings.danger_zones,
                    sensor_rules=self.settings.sensor_rules,
                    ppe_rules=self.settings.ppe_rules,
                )

                if detections:
                    analysis = build_analysis_result(
                        site_id=self.settings.site_id,
                        camera_id=self.settings.camera_id,
                        detections=detections,
                        sensor_snapshot=sensors,
                        frame_id=frame_index,
                        frame_ts=frame_ts,
                        frame_ts_source=frame_ts_source,
                        frame_shape=frame.shape,
                        zone_definitions=_zone_definitions(self.settings),
                    )

                    self.emitter.emit(analysis)

                    emitted += 1

                    if stop_after is not None and emitted >= stop_after:
                        logger.info("runtime stop: max_events=%d reached", stop_after)

                        return emitted

                frame_index += 1

        finally:
            self.sensor_hub.stop()

            self.source.release()

            self.emitter.close()

            logger.info(
                "runtime stop emitted=%d spool_pending=%d",
                emitted,
                self.emitter.pending_spool_size,
            )

        return emitted
