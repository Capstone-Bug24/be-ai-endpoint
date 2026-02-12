from __future__ import annotations

from pathlib import Path

import pytest

from capruntime.settings import load_runtime_settings


def test_load_settings_from_yaml(tmp_path: Path, sample_video: Path) -> None:
    cfg = tmp_path / "runtime.yaml"
    cfg.write_text(
        f"""
runtime:
  site_id: "SITE-X"
  camera_id: "cam-x"
  dry_run: true
source:
  type: "file"
  file_path: "{sample_video}"
model:
  type: "mock"
""",
        encoding="utf-8",
    )

    settings = load_runtime_settings(config_path=cfg)
    assert settings.site_id == "SITE-X"
    assert settings.camera_id == "cam-x"
    assert settings.source.file_path == str(sample_video)
    assert settings.model.type == "mock"


def test_invalid_source_type_raises(tmp_path: Path, sample_video: Path) -> None:
    cfg = tmp_path / "runtime.yaml"
    cfg.write_text(
        f"""
source:
  type: "invalid"
  file_path: "{sample_video}"
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported source.type") as exc:
        load_runtime_settings(config_path=cfg)
    assert "Unsupported source.type" in str(exc.value)
