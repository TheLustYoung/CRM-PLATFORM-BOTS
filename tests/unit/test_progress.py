from types import SimpleNamespace
from unittest.mock import MagicMock
from workers import tasks


def make_status():
    telegram = MagicMock()
    telegram.message.return_value = {"message_id": 5}
    job = SimpleNamespace(id="job-1", user_id=1, payload={})
    return tasks.Status(MagicMock(), job, telegram, "en", "bot"), telegram


def test_progress_is_throttled_and_formatted(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(tasks.time, "monotonic", lambda: clock[0])
    status, telegram = make_status()
    status.progress(20_000_000, 44_000_000)
    assert "45% (20.0 MB of 44.0 MB)" in telegram.message.call_args.args[1]
    status.progress(30_000_000, 44_000_000)  # within 3 s: skipped
    assert telegram.edit.call_count == 0
    clock[0] += 3.5
    status.progress(44_000_000, 44_000_000)
    assert "99%" in telegram.edit.call_args.args[2]  # 100% is reserved for the delivered result
    clock[0] += 3.5
    status.progress(5_000_000, None)
    assert "5.0 MB" in telegram.edit.call_args.args[2]


def test_same_text_is_not_edited_twice(monkeypatch):
    status, telegram = make_status()
    status.set("status_uploading")
    status.set("status_uploading")
    assert telegram.message.call_count == 1 and telegram.edit.call_count == 0
