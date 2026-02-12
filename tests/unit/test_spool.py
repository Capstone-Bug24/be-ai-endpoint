from __future__ import annotations

from pathlib import Path

from capruntime.spool import JsonlSpool


def test_spool_append_and_flush(tmp_path: Path) -> None:
    path = tmp_path / "pending.jsonl"
    spool = JsonlSpool(str(path))

    spool.append({"id": 1})
    spool.append({"id": 2})
    assert spool.size() == 2

    sent_ids: list[int] = []

    def send_ok(event: dict) -> bool:
        sent_ids.append(event["id"])
        return True

    sent, remaining = spool.flush(send_ok, batch_limit=100)
    assert sent == 2
    assert remaining == 0
    assert sent_ids == [1, 2]
    assert spool.size() == 0


def test_spool_stops_on_first_failure(tmp_path: Path) -> None:
    path = tmp_path / "pending.jsonl"
    spool = JsonlSpool(str(path))
    for idx in range(1, 5):
        spool.append({"id": idx})

    def send_fail_on_2(event: dict) -> bool:
        return event["id"] != 2

    sent, remaining = spool.flush(send_fail_on_2, batch_limit=100)
    assert sent == 1
    assert remaining == 3
    assert spool.size() == 3
