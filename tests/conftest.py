from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest


@pytest.fixture()
def sample_video(tmp_path: Path) -> Path:
    path = tmp_path / "sample.avi"
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(path), fourcc, 10.0, (320, 240))
    for i in range(20):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.circle(frame, (40 + i * 5, 120), 20, (0, 255, 0), -1)
        writer.write(frame)
    writer.release()
    return path
