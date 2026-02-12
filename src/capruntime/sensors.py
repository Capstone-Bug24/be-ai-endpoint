from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import threading
import time
from typing import Protocol

from .settings import SensorSettings


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SensorReader(Protocol):
    def read(self) -> dict | None:
        ...


@dataclass
class ConstantSensor:
    value: float

    def read(self) -> dict:
        return {"value": self.value}


@dataclass
class JsonlReplaySensor:
    path: str
    loop: bool = True

    def __post_init__(self) -> None:
        p = Path(self.path)
        if not p.exists():
            raise FileNotFoundError(f"sensor jsonl file not found: {self.path}")
        self._lines = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        self._idx = 0

    def read(self) -> dict | None:
        if not self._lines:
            return None
        if self._idx >= len(self._lines):
            if not self.loop:
                return None
            self._idx = 0
        raw = self._lines[self._idx]
        self._idx += 1
        return json.loads(raw)


class SensorWorker:
    def __init__(self, name: str, reader: SensorReader, interval_sec: float) -> None:
        self._name = name
        self._reader = reader
        self._interval = max(0.01, interval_sec)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name=f"sensor-{name}", daemon=True)
        self._lock = threading.Lock()
        self._latest: dict | None = None
        self._errors = 0

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                payload = self._reader.read()
                if payload is not None:
                    with self._lock:
                        self._latest = {
                            "sensor": self._name,
                            "ts": _now_iso(),
                            "data": payload,
                        }
            except Exception:
                self._errors += 1
            time.sleep(self._interval)

    def snapshot(self) -> dict | None:
        with self._lock:
            if self._latest is None:
                return None
            return dict(self._latest)

    @property
    def errors(self) -> int:
        return self._errors


def _build_reader(cfg: SensorSettings) -> SensorReader:
    if cfg.type == "constant":
        return ConstantSensor(value=cfg.constant_value)
    if cfg.type == "jsonl":
        if not cfg.jsonl_path:
            raise ValueError(f"jsonl_path is required for sensor '{cfg.name}'")
        return JsonlReplaySensor(path=cfg.jsonl_path, loop=cfg.loop)
    raise ValueError(f"unsupported sensor type: {cfg.type}")


class SensorHub:
    def __init__(self, sensor_settings: list[SensorSettings]) -> None:
        self._workers: list[SensorWorker] = []
        for cfg in sensor_settings:
            reader = _build_reader(cfg)
            self._workers.append(
                SensorWorker(
                    name=cfg.name,
                    reader=reader,
                    interval_sec=cfg.interval_sec,
                )
            )

    def start(self) -> None:
        for worker in self._workers:
            worker.start()

    def stop(self) -> None:
        for worker in self._workers:
            worker.stop()

    def snapshot(self) -> dict[str, dict]:
        data: dict[str, dict] = {}
        for worker in self._workers:
            item = worker.snapshot()
            if item is not None:
                data[item["sensor"]] = item
        return data

    def health(self) -> dict[str, int]:
        return {worker._name: worker.errors for worker in self._workers}  # noqa: SLF001
