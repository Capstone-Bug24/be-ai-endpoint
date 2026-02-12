from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest


def _write_sample_video(path: Path, codec: str) -> bool:
    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(str(path), fourcc, 10.0, (320, 240))
    if not writer.isOpened():
        writer.release()
        return False

    for i in range(20):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.circle(frame, (40 + i * 5, 120), 20, (0, 255, 0), -1)
        writer.write(frame)
    writer.release()

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        cap.release()
        return False
    ok, _ = cap.read()
    cap.release()
    return bool(ok)


@pytest.fixture()
def sample_video(tmp_path: Path) -> Path:
    candidates = [
        ("sample_mjpg.avi", "MJPG"),
        ("sample_xvid.avi", "XVID"),
        ("sample_mp4v.mp4", "mp4v"),
    ]
    for filename, codec in candidates:
        path = tmp_path / filename
        if _write_sample_video(path, codec):
            return path
    pytest.skip("OpenCV video codecs unavailable on this runner; skipping video-based tests")
