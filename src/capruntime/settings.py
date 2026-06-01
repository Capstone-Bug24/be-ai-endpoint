from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os

import yaml


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


@dataclass(frozen=True)
class SourceSettings:
    type: str = "file"  # file | rtsp | webcam
    rtsp_url: str | None = None
    file_path: str | None = None
    webcam_index: int = 0
    loop: bool = False


@dataclass(frozen=True)
class ModelSettings:
    type: str = "mock"  # mock | yolo | onnx
    score_threshold: float = 0.25
    yolo_model_path: str | None = None
    onnx_model_path: str | None = None
    device: str | None = None
    tracking: bool = False
    tracker: str = "bytetrack.yaml"


@dataclass(frozen=True)
class SensorSettings:
    name: str
    type: str = "constant"  # constant | jsonl
    sensor_id: str | None = None
    sensor_type: str = "generic"
    unit: str | None = None
    zone_ids: tuple[str, ...] = ()
    interval_sec: float = 1.0
    constant_value: float = 0.0
    jsonl_path: str | None = None
    loop: bool = True


@dataclass(frozen=True)
class DangerZoneSettings:
    zone_id: str
    type: str = "quadrant"  # quadrant | polygon
    quadrant: int = 1
    severity: str = "MEDIUM"
    name: str | None = None
    points: tuple[tuple[float, float], ...] = ()
    points_norm: tuple[tuple[float, float], ...] = ()
    basis: str = "bbox_bottom_band"
    min_overlap_ratio: float = 0.2
    foot_band_ratio: float = 0.18


@dataclass(frozen=True)
class SensorRuleSettings:
    sensor: str
    less_than: float | None = None
    greater_than: float | None = None
    severity: str = "HIGH"
    event_type: str = "PROXIMITY_RISK"


@dataclass(frozen=True)
class PpeRuleSettings:
    enabled: bool = False
    required: tuple[str, ...] = ("helmet", "vest")
    min_person_confidence: float = 0.45
    min_ppe_confidence: float = 0.35
    severity: str = "HIGH"
    infer_missing_when_absent: bool = False


@dataclass(frozen=True)
class BackendSettings:
    url: str = "http://127.0.0.1:8080/api/ai/events"
    timeout_sec: float = 10.0


@dataclass(frozen=True)
class SpoolSettings:
    file_path: str = "outputs/spool/pending_events.jsonl"
    flush_batch: int = 100


@dataclass(frozen=True)
class RuntimeSettings:
    site_id: str = "S001"
    camera_id: str = "cam01"
    timezone: str | None = "UTC"
    fps_limit: int = 10
    max_events: int | None = None
    dry_run: bool = True
    output_jsonl: str | None = None
    source: SourceSettings = field(default_factory=SourceSettings)
    model: ModelSettings = field(default_factory=ModelSettings)
    sensors: list[SensorSettings] = field(default_factory=list)
    danger_zones: list[DangerZoneSettings] = field(default_factory=list)
    sensor_rules: list[SensorRuleSettings] = field(default_factory=list)
    ppe_rules: PpeRuleSettings = field(default_factory=PpeRuleSettings)
    backend: BackendSettings = field(default_factory=BackendSettings)
    spool: SpoolSettings = field(default_factory=SpoolSettings)


def _default_config() -> dict[str, Any]:
    return {
        "runtime": {
            "site_id": "S001",
            "camera_id": "cam01",
            "timezone": "UTC",
            "fps_limit": 10,
            "max_events": None,
            "dry_run": True,
            "output_jsonl": None,
        },
        "source": {
            "type": "file",
            "rtsp_url": None,
            "file_path": None,
            "webcam_index": 0,
            "loop": False,
        },
        "model": {
            "type": "mock",
            "score_threshold": 0.25,
            "yolo_model_path": None,
            "onnx_model_path": None,
            "device": None,
            "tracking": False,
            "tracker": "bytetrack.yaml",
        },
        "sensors": [],
        "rules": {
            "danger_zones": [],
            "sensor_thresholds": [],
            "ppe": {
                "enabled": False,
                "required": ["helmet", "vest"],
                "min_person_confidence": 0.45,
                "min_ppe_confidence": 0.35,
                "severity": "HIGH",
                "infer_missing_when_absent": False,
            },
        },
        "backend": {
            "url": "http://127.0.0.1:8080/api/ai/events",
            "timeout_sec": 10.0,
        },
        "spool": {
            "file_path": "outputs/spool/pending_events.jsonl",
            "flush_batch": 100,
        },
    }


def _env_overrides() -> dict[str, Any]:
    out: dict[str, Any] = {}

    runtime: dict[str, Any] = {}
    source: dict[str, Any] = {}
    model: dict[str, Any] = {}
    backend: dict[str, Any] = {}
    spool: dict[str, Any] = {}

    if os.getenv("CR_SITE_ID"):
        runtime["site_id"] = os.getenv("CR_SITE_ID")
    if os.getenv("CR_CAMERA_ID"):
        runtime["camera_id"] = os.getenv("CR_CAMERA_ID")
    if os.getenv("CR_TIMEZONE"):
        runtime["timezone"] = os.getenv("CR_TIMEZONE")
    if os.getenv("CR_FPS_LIMIT"):
        runtime["fps_limit"] = int(os.getenv("CR_FPS_LIMIT", "10"))
    if os.getenv("CR_MAX_EVENTS"):
        runtime["max_events"] = int(os.getenv("CR_MAX_EVENTS", "0"))
    if os.getenv("CR_DRY_RUN"):
        runtime["dry_run"] = _as_bool(os.getenv("CR_DRY_RUN"), default=False)
    if os.getenv("CR_OUTPUT_JSONL"):
        runtime["output_jsonl"] = os.getenv("CR_OUTPUT_JSONL")

    if os.getenv("CR_SOURCE_TYPE"):
        source["type"] = os.getenv("CR_SOURCE_TYPE")
    if os.getenv("CR_RTSP_URL"):
        source["rtsp_url"] = os.getenv("CR_RTSP_URL")
    if os.getenv("CR_FILE_PATH"):
        source["file_path"] = os.getenv("CR_FILE_PATH")
    if os.getenv("CR_WEBCAM_INDEX"):
        source["webcam_index"] = int(os.getenv("CR_WEBCAM_INDEX", "0"))
    if os.getenv("CR_SOURCE_LOOP"):
        source["loop"] = _as_bool(os.getenv("CR_SOURCE_LOOP"), default=False)

    if os.getenv("CR_MODEL_TYPE"):
        model["type"] = os.getenv("CR_MODEL_TYPE")
    if os.getenv("CR_MODEL_SCORE_THRESHOLD"):
        model["score_threshold"] = float(os.getenv("CR_MODEL_SCORE_THRESHOLD", "0.25"))
    if os.getenv("CR_YOLO_MODEL_PATH"):
        model["yolo_model_path"] = os.getenv("CR_YOLO_MODEL_PATH")
    if os.getenv("CR_ONNX_MODEL_PATH"):
        model["onnx_model_path"] = os.getenv("CR_ONNX_MODEL_PATH")
    if os.getenv("CR_MODEL_DEVICE"):
        model["device"] = os.getenv("CR_MODEL_DEVICE")
    if os.getenv("CR_MODEL_TRACKING"):
        model["tracking"] = _as_bool(os.getenv("CR_MODEL_TRACKING"), default=False)
    if os.getenv("CR_MODEL_TRACKER"):
        model["tracker"] = os.getenv("CR_MODEL_TRACKER")

    if os.getenv("CR_BACKEND_URL"):
        backend["url"] = os.getenv("CR_BACKEND_URL")
    if os.getenv("CR_BACKEND_TIMEOUT_SEC"):
        backend["timeout_sec"] = float(os.getenv("CR_BACKEND_TIMEOUT_SEC", "10.0"))

    if os.getenv("CR_SPOOL_FILE_PATH"):
        spool["file_path"] = os.getenv("CR_SPOOL_FILE_PATH")
    if os.getenv("CR_SPOOL_FLUSH_BATCH"):
        spool["flush_batch"] = int(os.getenv("CR_SPOOL_FLUSH_BATCH", "100"))

    if runtime:
        out["runtime"] = runtime
    if source:
        out["source"] = source
    if model:
        out["model"] = model
    if backend:
        out["backend"] = backend
    if spool:
        out["spool"] = spool
    return out


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    if content is None:
        return {}
    if not isinstance(content, dict):
        raise ValueError(f"Top-level config must be mapping: {path}")
    return content


def _parse_points(value: Any, field_name: str) -> tuple[tuple[float, float], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    points: list[tuple[float, float]] = []
    for point in value:
        if isinstance(point, dict):
            if "x" not in point or "y" not in point:
                raise ValueError(f"{field_name} entries must contain x and y")
            points.append((float(point["x"]), float(point["y"])))
        elif isinstance(point, (list, tuple)) and len(point) == 2:
            points.append((float(point[0]), float(point[1])))
        else:
            raise ValueError(f"{field_name} entries must be {{x, y}} or [x, y]")
    return tuple(points)


def _parse_string_list(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        text = value.strip()
        return (text,) if text else ()
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list or string")
    return tuple(str(item).strip() for item in value if str(item).strip())


def _to_settings(cfg: dict[str, Any]) -> RuntimeSettings:
    runtime_cfg = cfg.get("runtime", {})
    source_cfg = cfg.get("source", {})
    model_cfg = cfg.get("model", {})
    backend_cfg = cfg.get("backend", {})
    spool_cfg = cfg.get("spool", {})
    sensors_cfg = cfg.get("sensors", [])
    rules_cfg = cfg.get("rules", {})
    danger_zones_cfg = rules_cfg.get("danger_zones", [])
    sensor_rules_cfg = rules_cfg.get("sensor_thresholds", [])
    ppe_rules_cfg = rules_cfg.get("ppe", {})

    source = SourceSettings(
        type=str(source_cfg.get("type", "file")).strip().lower(),
        rtsp_url=source_cfg.get("rtsp_url"),
        file_path=source_cfg.get("file_path"),
        webcam_index=int(source_cfg.get("webcam_index", 0)),
        loop=_as_bool(source_cfg.get("loop"), default=False),
    )
    model = ModelSettings(
        type=str(model_cfg.get("type", "mock")).strip().lower(),
        score_threshold=float(model_cfg.get("score_threshold", 0.25)),
        yolo_model_path=model_cfg.get("yolo_model_path"),
        onnx_model_path=model_cfg.get("onnx_model_path"),
        device=model_cfg.get("device"),
        tracking=_as_bool(model_cfg.get("tracking"), default=False),
        tracker=str(model_cfg.get("tracker", "bytetrack.yaml")).strip()
        or "bytetrack.yaml",
    )

    sensors: list[SensorSettings] = []
    if not isinstance(sensors_cfg, list):
        raise ValueError("sensors must be a list")
    for item in sensors_cfg:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        sensors.append(
            SensorSettings(
                name=name,
                type=str(item.get("type", "constant")).strip().lower(),
                sensor_id=item.get("id") or item.get("sensor_id"),
                sensor_type=str(item.get("sensor_type", item.get("kind", "generic")))
                .strip()
                .lower(),
                unit=item.get("unit"),
                zone_ids=_parse_string_list(item.get("zone_ids"), "sensors[].zone_ids"),
                interval_sec=float(item.get("interval_sec", 1.0)),
                constant_value=float(item.get("constant_value", 0.0)),
                jsonl_path=item.get("jsonl_path"),
                loop=_as_bool(item.get("loop"), default=True),
            )
        )

    danger_zones: list[DangerZoneSettings] = []
    if not isinstance(danger_zones_cfg, list):
        raise ValueError("rules.danger_zones must be a list")
    for item in danger_zones_cfg:
        if not isinstance(item, dict):
            continue
        zone_id = str(item.get("zone_id", "")).strip()
        if not zone_id:
            continue
        danger_zones.append(
            DangerZoneSettings(
                zone_id=zone_id,
                type=str(item.get("type", "quadrant")).strip().lower(),
                quadrant=int(item.get("quadrant", 1)),
                severity=str(item.get("severity", "MEDIUM")).strip().upper(),
                name=item.get("name"),
                points=_parse_points(item.get("points"), "rules.danger_zones[].points"),
                points_norm=_parse_points(
                    item.get("points_norm"), "rules.danger_zones[].points_norm"
                ),
                basis=str(item.get("basis", "bbox_bottom_band")).strip().lower(),
                min_overlap_ratio=float(item.get("min_overlap_ratio", 0.2)),
                foot_band_ratio=float(item.get("foot_band_ratio", 0.18)),
            )
        )

    sensor_rules: list[SensorRuleSettings] = []
    if not isinstance(sensor_rules_cfg, list):
        raise ValueError("rules.sensor_thresholds must be a list")
    for item in sensor_rules_cfg:
        if not isinstance(item, dict):
            continue
        sensor = str(item.get("sensor", "")).strip()
        if not sensor:
            continue
        sensor_rules.append(
            SensorRuleSettings(
                sensor=sensor,
                less_than=float(item["less_than"])
                if item.get("less_than") is not None
                else None,
                greater_than=float(item["greater_than"])
                if item.get("greater_than") is not None
                else None,
                severity=str(item.get("severity", "HIGH")).strip().upper(),
                event_type=str(item.get("event_type", "PROXIMITY_RISK"))
                .strip()
                .upper(),
            )
        )

    if not isinstance(ppe_rules_cfg, dict):
        raise ValueError("rules.ppe must be a mapping")
    ppe_required_raw = ppe_rules_cfg.get("required", ["helmet", "vest"])
    if isinstance(ppe_required_raw, str):
        ppe_required = (
            (ppe_required_raw.strip().lower(),) if ppe_required_raw.strip() else ()
        )
    elif isinstance(ppe_required_raw, list):
        ppe_required = tuple(
            str(item).strip().lower() for item in ppe_required_raw if str(item).strip()
        )
    else:
        raise ValueError("rules.ppe.required must be a list or string")
    ppe_rules = PpeRuleSettings(
        enabled=_as_bool(ppe_rules_cfg.get("enabled"), default=False),
        required=ppe_required,
        min_person_confidence=float(ppe_rules_cfg.get("min_person_confidence", 0.45)),
        min_ppe_confidence=float(ppe_rules_cfg.get("min_ppe_confidence", 0.35)),
        severity=str(ppe_rules_cfg.get("severity", "HIGH")).strip().upper(),
        infer_missing_when_absent=_as_bool(
            ppe_rules_cfg.get("infer_missing_when_absent"),
            default=False,
        ),
    )

    settings = RuntimeSettings(
        site_id=str(runtime_cfg.get("site_id", "S001")),
        camera_id=str(runtime_cfg.get("camera_id", "cam01")),
        timezone=runtime_cfg.get("timezone", "UTC"),
        fps_limit=max(0, int(runtime_cfg.get("fps_limit", 10))),
        max_events=runtime_cfg.get("max_events"),
        dry_run=_as_bool(runtime_cfg.get("dry_run"), default=True),
        output_jsonl=runtime_cfg.get("output_jsonl"),
        source=source,
        model=model,
        sensors=sensors,
        danger_zones=danger_zones,
        sensor_rules=sensor_rules,
        ppe_rules=ppe_rules,
        backend=BackendSettings(
            url=str(backend_cfg.get("url", "http://127.0.0.1:8080/api/ai/events")),
            timeout_sec=float(backend_cfg.get("timeout_sec", 10.0)),
        ),
        spool=SpoolSettings(
            file_path=str(
                spool_cfg.get("file_path", "outputs/spool/pending_events.jsonl")
            ),
            flush_batch=max(1, int(spool_cfg.get("flush_batch", 100))),
        ),
    )

    if settings.source.type not in {"file", "rtsp", "webcam"}:
        raise ValueError(f"Unsupported source.type: {settings.source.type}")
    if settings.model.type not in {"mock", "yolo", "onnx"}:
        raise ValueError(f"Unsupported model.type: {settings.model.type}")
    for zone in settings.danger_zones:
        if zone.type not in {"quadrant", "polygon"}:
            raise ValueError(f"Unsupported danger zone type: {zone.type}")
        if zone.type == "quadrant" and zone.quadrant not in {1, 2, 3, 4}:
            raise ValueError(f"Unsupported quadrant: {zone.quadrant}")
        if (
            zone.type == "polygon"
            and len(zone.points) < 3
            and len(zone.points_norm) < 3
        ):
            raise ValueError(f"Polygon zone requires at least 3 points: {zone.zone_id}")
    if settings.source.type == "file" and not settings.source.file_path:
        raise ValueError("source.file_path is required when source.type=file")
    if settings.source.type == "rtsp" and not settings.source.rtsp_url:
        raise ValueError("source.rtsp_url is required when source.type=rtsp")
    return settings


def load_runtime_settings(
    config_path: str | Path = "configs/runtime.yaml",
    cli_overrides: dict[str, Any] | None = None,
) -> RuntimeSettings:
    cfg = _default_config()
    yaml_cfg = _load_yaml(Path(config_path))
    cfg = _deep_merge(cfg, yaml_cfg)
    cfg = _deep_merge(cfg, _env_overrides())
    if cli_overrides:
        cfg = _deep_merge(cfg, cli_overrides)
    return _to_settings(cfg)
