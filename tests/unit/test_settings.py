from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from capruntime.settings import load_runtime_settings


def test_load_settings_from_yaml(tmp_path: Path, sample_video: Path) -> None:
    cfg = tmp_path / "runtime.yaml"
    cfg_data = {
        "runtime": {"site_id": "SITE-X", "camera_id": "cam-x", "dry_run": True},
        "source": {"type": "file", "file_path": str(sample_video)},
        "model": {"type": "mock"},
        "sensors": [
            {
                "name": "ultra_front",
                "id": "ultra_front_01",
                "sensor_type": "ultrasonic",
                "unit": "m",
                "zone_ids": ["danger_q1"],
            }
        ],
    }
    cfg.write_text(
        yaml.safe_dump(cfg_data, sort_keys=False),
        encoding="utf-8",
    )

    settings = load_runtime_settings(config_path=cfg)
    assert settings.site_id == "SITE-X"
    assert settings.camera_id == "cam-x"
    assert settings.source.file_path == str(sample_video)
    assert settings.model.type == "mock"
    assert settings.sensors[0].sensor_id == "ultra_front_01"
    assert settings.sensors[0].sensor_type == "ultrasonic"
    assert settings.sensors[0].unit == "m"
    assert settings.sensors[0].zone_ids == ("danger_q1",)


def test_model_device_override(tmp_path: Path, sample_video: Path) -> None:
    cfg = tmp_path / "runtime.yaml"
    cfg.write_text(
        yaml.safe_dump(
            {
                "source": {"type": "file", "file_path": str(sample_video)},
                "model": {"type": "yolo", "yolo_model_path": "models/yolov8n.pt"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    settings = load_runtime_settings(
        config_path=cfg,
        cli_overrides={
            "model": {"device": "cuda:0", "tracking": True, "tracker": "bytetrack.yaml"}
        },
    )

    assert settings.model.device == "cuda:0"
    assert settings.model.tracking is True
    assert settings.model.tracker == "bytetrack.yaml"


def test_invalid_source_type_raises(tmp_path: Path) -> None:
    cfg = tmp_path / "runtime.yaml"
    cfg.write_text(yaml.safe_dump({"source": {"type": "invalid"}}), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported source.type") as exc:
        load_runtime_settings(config_path=cfg)
    assert "Unsupported source.type" in str(exc.value)
