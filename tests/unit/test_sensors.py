from __future__ import annotations

from pathlib import Path
import time

from capruntime.sensors import JsonlReplaySensor, SensorHub
from capruntime.settings import SensorSettings


def test_jsonl_sensor_replay(tmp_path: Path) -> None:
    path = tmp_path / "sensor.jsonl"
    path.write_text('{"v": 1}\n{"v": 2}\n', encoding="utf-8")
    sensor = JsonlReplaySensor(path=str(path), loop=False)

    assert sensor.read() == {"v": 1}
    assert sensor.read() == {"v": 2}
    assert sensor.read() is None


def test_sensor_hub_collects_multiple_sensors() -> None:
    sensors = [
        SensorSettings(name="s1", type="constant", interval_sec=0.01, constant_value=1.0),
        SensorSettings(name="s2", type="constant", interval_sec=0.01, constant_value=2.0),
    ]
    hub = SensorHub(sensors)
    hub.start()
    try:
        time.sleep(0.05)
        snapshot = hub.snapshot()
    finally:
        hub.stop()

    assert "s1" in snapshot
    assert "s2" in snapshot
    assert snapshot["s1"]["data"]["value"] == 1.0
    assert snapshot["s2"]["data"]["value"] == 2.0
