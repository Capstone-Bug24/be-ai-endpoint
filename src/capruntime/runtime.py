from __future__ import annotations

import logging
import time

from .emitter import ResilientEmitter
from .events import build_event
from .model import ModelRunner, create_model_runner
from .sensors import SensorHub
from .settings import RuntimeSettings
from .video import VideoSource, create_video_source

logger = logging.getLogger(__name__)


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
        period = 0.0 if self.settings.fps_limit <= 0 else 1.0 / float(self.settings.fps_limit)
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

                detections = self.model_runner.infer(frame, frame_index)
                sensors = self.sensor_hub.snapshot()
                for detection in detections:
                    event = build_event(
                        site_id=self.settings.site_id,
                        camera_id=self.settings.camera_id,
                        detection=detection,
                        sensor_snapshot=sensors,
                    )
                    self.emitter.emit(event)
                    emitted += 1
                    if stop_after is not None and emitted >= stop_after:
                        logger.info("runtime stop: max_events=%d reached", stop_after)
                        return emitted
                frame_index += 1
        finally:
            self.sensor_hub.stop()
            self.source.release()
            self.emitter.close()
            logger.info("runtime stop emitted=%d spool_pending=%d", emitted, self.emitter.pending_spool_size)
        return emitted
