from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Protocol

import cv2
import numpy as np

from .settings import SourceSettings


class VideoSource(Protocol):
    @property
    def is_live(self) -> bool:
        ...

    def read(self) -> tuple[bool, np.ndarray | None]:
        ...

    def frame_timestamp(self) -> tuple[str | None, str | None]:
        ...

    def release(self) -> None:
        ...


@dataclass
class FileVideoSource:
    path: str
    loop: bool = False

    def __post_init__(self) -> None:
        self._cap = cv2.VideoCapture(self.path)
        if not self._cap.isOpened():
            raise RuntimeError(f"Unable to open video file: {self.path}")

    @property
    def is_live(self) -> bool:
        return False

    def read(self) -> tuple[bool, np.ndarray | None]:
        ok, frame = self._cap.read()
        if ok:
            return True, frame
        if not self.loop:
            return False, None
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        return self._cap.read()

    def frame_timestamp(self) -> tuple[str | None, str | None]:
        return None, None

    def release(self) -> None:
        self._cap.release()


@dataclass
class WebcamVideoSource:
    index: int = 0

    def __post_init__(self) -> None:
        self._cap = cv2.VideoCapture(self.index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Unable to open webcam: index={self.index}")

    @property
    def is_live(self) -> bool:
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        return self._cap.read()

    def frame_timestamp(self) -> tuple[str | None, str | None]:
        return None, None

    def release(self) -> None:
        self._cap.release()


@dataclass
class RtspVideoSource:
    url: str
    initial_backoff_sec: float = 0.5
    max_backoff_sec: float = 8.0

    def __post_init__(self) -> None:
        self._backoff = self.initial_backoff_sec
        self._cap = self._open_capture()

    def _open_capture(self) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(self.url)
        return cap

    @property
    def is_live(self) -> bool:
        return True

    def _reconnect(self) -> None:
        self._cap.release()
        time.sleep(self._backoff)
        self._cap = self._open_capture()
        if self._cap.isOpened():
            self._backoff = self.initial_backoff_sec
        else:
            self._backoff = min(self.max_backoff_sec, self._backoff * 2.0)

    def read(self) -> tuple[bool, np.ndarray | None]:
        ok, frame = self._cap.read()
        if ok:
            return True, frame
        self._reconnect()
        return False, None

    def frame_timestamp(self) -> tuple[str | None, str | None]:
        return None, None

    def release(self) -> None:
        self._cap.release()


def create_video_source(source: SourceSettings) -> VideoSource:
    if source.type == "file":
        return FileVideoSource(path=str(source.file_path), loop=source.loop)
    if source.type == "webcam":
        return WebcamVideoSource(index=source.webcam_index)
    if source.type == "rtsp":
        return RtspVideoSource(url=str(source.rtsp_url))
    raise ValueError(f"Unsupported source type: {source.type}")
