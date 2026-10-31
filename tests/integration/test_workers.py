from contextlib import contextmanager
from unittest.mock import MagicMock
import fakeredis
import pytest
from moto import mock_aws
from sqlalchemy import select, func
from backend.models import Job, Usage, UploadedFile
from backend.services import users
from backend.services.security import DomainError
from workers import tasks
import storage


def worker_fakes(db, monkeypatch, tmp_path):
    @contextmanager
    def session():
        yield db
    monkeypatch.setattr(tasks, "Session", session)
    monkeypatch.setattr(tasks, "redis_client", lambda: fakeredis.FakeRedis())
    monkeypatch.setattr(tasks.cfg, "temp_root", str(tmp_path))
    monkeypatch.setattr(tasks.cfg, "min_free_disk_bytes", 0)
    telegram = MagicMock()
    telegram.message.return_value = {"message_id": 10}
    monkeypatch.setattr(tasks, "Telegram", lambda _: telegram)
    adapter = MagicMock()
    monkeypatch.setattr(tasks, "MediaAdapter", lambda: adapter)
    return telegram, adapter


def make_job(db, **values):
    users.register(db, values.get("bot_id", "video"), 42)
    job = Job(user_id=42, **{"bot_id": "video", "request_key": "r", "platform": "archive", **values})
    db.add(job)
    db.flush()
    db.add(Usage(user_id=42, bot_id=job.bot_id, job_id=job.id))
    db.commit()
    return job


def test_metadata_card_sent_with_attribution(db, monkeypatch, tmp_path):
    telegram, adapter = worker_fakes(db, monkeypatch, tmp_path)
    job = make_job(db, kind="metadata", source_url="https://archive.org/details/x")
    adapter.extract.return_value = {"platform": "archive", "title": "Clip", "thumbnail": None, "views": 5, "likes": None,
                                    "formats": [{"selector": "18", "kind": "video", "label": "MP4 · 360p", "size": 1000}]}
    tasks.run(job.id)
    assert db.get(Job, job.id).status == "completed"
    text, buttons = telegram.message.call_args_list[-1].args[1:3]
    assert "@video_test_bot" in text and "MP4 · 360p" in text and "not available" in text
    assert buttons[0][0]["callback_data"] == f"dl:{job.id}:0"
    telegram.delete.assert_called_once_with(42, 10)  # status message removed


def test_download_stored_delivered_once(db, monkeypatch, tmp_path):
    telegram, adapter = worker_fakes(db, monkeypatch, tmp_path)
    job = make_job(db, kind="download", source_url="https://archive.org/details/x", selected_format="18", payload={"merge": None})

    def download(url, selector, root, max_size, merge, on_progress=None, should_stop=None):
        file = root / "video.mp4"
        file.write_bytes(b"test output")
        return [file]
    adapter.download.side_effect = download
    with mock_aws():
        storage.ensure_bucket()
        tasks.run(job.id)
        assert db.get(Job, job.id).status == "completed"
        assert db.scalar(select(func.count()).select_from(UploadedFile)) == 1
        assert telegram.media.call_args.args[2] == "" and telegram.document.call_count == 1  # clean video + the file
        text = telegram.message.call_args_list[-1].args[1]
        assert "@video_test_bot" in text and "video.mp4" in text and "⬇" in text
        assert [p for p in tmp_path.iterdir() if p.is_dir()] == []  # temp cleaned
        tasks.run(job.id)
        assert adapter.download.call_count == 1 and telegram.media.call_count == 1


def test_collection_sent_as_album_with_single_caption(db, monkeypatch, tmp_path):
    telegram, adapter = worker_fakes(db, monkeypatch, tmp_path)
    job = make_job(db, bot_id="media", kind="download", platform="wikimedia", source_url="https://commons.wikimedia.org/wiki/File:x.jpg", selected_format="best",
                   payload={"title": "Caption"})

    def download(url, selector, root, max_size, merge, on_progress=None, should_stop=None):
        paths = []
        for i in range(3):
            path = root / f"00{i}-img.jpg"
            path.write_bytes(b"jpg")
            paths.append(path)
        return paths
    adapter.download.side_effect = download
    with mock_aws():
        storage.ensure_bucket()
        tasks.run(job.id)
    assert db.get(Job, job.id).status == "completed"
    chat, paths, caption = telegram.media_group.call_args.args
    assert [p.name for p in paths] == ["000-img.jpg", "001-img.jpg", "002-img.jpg"]
    assert caption == ""  # a clean album; the post text follows as its own message
    text = telegram.message.call_args_list[-1].args[1]
    assert "Caption" in text and "@media_test_bot" in text


def test_failure_isolated_and_reported(db, monkeypatch, tmp_path):
    telegram, adapter = worker_fakes(db, monkeypatch, tmp_path)
    failed = make_job(db, kind="metadata", request_key="1", source_url="https://archive.org/details/x")
    other = make_job(db, kind="metadata", request_key="2", source_url="https://archive.org/details/y")
    adapter.extract.side_effect = DomainError("unavailable")
    tasks.run(failed.id)
    assert db.get(Job, failed.id).status == "failed" and db.get(Job, failed.id).error == "unavailable"
    assert db.get(Job, other.id).status == "queued"
    assert "unavailable" in telegram.message.call_args.args[1]


def test_failed_job_refunds_the_daily_limit(db, monkeypatch, tmp_path):
    telegram, adapter = worker_fakes(db, monkeypatch, tmp_path)
    job = make_job(db, kind="download", request_key="refund", source_url="https://archive.org/details/x", selected_format="18",
                   result={"title": "T"})
    adapter.download.side_effect = DomainError("unavailable")
    tasks.run(job.id)
    assert db.get(Job, job.id).status == "failed"
    assert db.scalar(select(func.count()).select_from(Usage).where(Usage.job_id == job.id)) == 0


def test_cancel_button_stops_a_running_download(db, monkeypatch, tmp_path):
    telegram, adapter = worker_fakes(db, monkeypatch, tmp_path)
    redis = fakeredis.FakeRedis()
    monkeypatch.setattr(tasks, "redis_client", lambda: redis)
    job = make_job(db, kind="download", request_key="cancel", source_url="https://archive.org/details/x", selected_format="18",
                   result={"title": "T"})

    def download(*args, **kwargs):
        redis.set(f"cancel:{job.id}", "1")  # the user presses Cancel while bytes arrive
        assert kwargs["should_stop"]()  # the download loop sees it
        raise DomainError("cancelled")

    adapter.download.side_effect = download
    tasks.run(job.id)
    saved = db.get(Job, job.id)
    assert saved.status == "failed" and saved.error == "cancelled"
    assert db.scalar(select(func.count()).select_from(Usage).where(Usage.job_id == job.id)) == 0  # limit refunded
    assert "Cancelled" in telegram.message.call_args_list[-1].args[1]


def test_status_message_has_cancel_button(db, monkeypatch, tmp_path):
    telegram, adapter = worker_fakes(db, monkeypatch, tmp_path)
    job = make_job(db, kind="download", request_key="button", source_url="https://archive.org/details/x", selected_format="18")
    status = tasks.Status(db, job, telegram, "en", "bot")
    status.set("status_downloading")
    assert telegram.message.call_args.args[2] == [[{"text": "✖️ Cancel", "callback_data": f"cx:{job.id}"}]]
    status.set("status_sending")
    assert telegram.edit.call_args.args[3] is None  # too late to cancel: the button disappears
