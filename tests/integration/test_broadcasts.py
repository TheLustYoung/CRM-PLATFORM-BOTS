from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import MagicMock
from sqlalchemy import func, select
from backend.models import Broadcast, BroadcastMessage, User, now
from backend.services import broadcasts, monetization, queue, users
from workers import broadcast as worker
from workers.telegram import TelegramError


def test_editor_html_is_rebuilt_from_an_allow_list():
    dirty = ('<b>Sale</b> <span class="tg-spoiler">-50%</span> <script>alert(1)</script><a href="javascript:x">bad</a> '
             '<a href="https://shop.example/?a=1&b=2">shop</a><blockquote expandable>q</blockquote><i onclick="x">it</i><unknown>t</unknown>')
    text, visible = broadcasts.clean(dirty)
    assert text == ('<b>Sale</b> <tg-spoiler>-50%</tg-spoiler> alert(1)bad <a href="https://shop.example/?a=1&amp;b=2">shop</a>'
                    '<blockquote expandable>q</blockquote><i>it</i>t')
    assert visible == len("Sale -50% alert(1)bad shopqitt")
    assert broadcasts.clean("<b>unclosed")[0] == "<b>unclosed</b>"
    assert broadcasts.clean("a<br>b")[0] == "a\nb"


def test_post_limits_follow_telegram():
    assert broadcasts.validate("<b>hi</b>", "", "", None, ["media"]) == "<b>hi</b>"
    for args, message in [(("", "", "", None, ["media"]), "Write"), (("x" * 1025, "", "", b"jpg", ["media"]), "1025 of 1024"),
                          (("hi", "Open", "", None, ["media"]), "both"), (("hi", "Open", "ftp://x", None, ["media"]), "https"),
                          (("hi", "", "", None, []), "bot")]:
        try:
            broadcasts.validate(*args)
            raise AssertionError("should fail")
        except ValueError as error:
            assert message in str(error)


def people(db):
    """1 uses media+youtube, 2 media, 3 youtube, 4 banned, 5 Premium."""
    for user_id, bots in {1: ["media", "video"], 2: ["media"], 3: ["video"], 4: ["media"], 5: ["media"]}.items():
        for bot in bots:
            users.register(db, bot, user_id)
    db.get(User, 4).banned = True
    db.commit()
    monetization.grant(db, db.get(User, 5), 30, "admin")


def test_audience_counts_each_person_once_and_respects_premium(db):
    people(db)
    assert broadcasts.audience(db, ["media", "video"], True) == {"total": 3, "per_bot": {"media": 2, "video": 2}}
    assert broadcasts.audience(db, ["media", "video"], False)["total"] == 4
    b = Broadcast(text="hi", bots=["video", "media"], skip_premium=True, audience=3, created_by="x", photo_ids={})
    db.add(b)
    db.commit()
    assert broadcasts.next_batch(db, b, 10) == [(1, "video"), (2, "media"), (3, "video")]  # first selected bot wins


def fake_worker(db, monkeypatch):
    @contextmanager
    def session():
        yield db
    telegram = MagicMock()
    telegram.call.side_effect = lambda method, data, files=None: {"message_id": 100 + data["chat_id"]}
    monkeypatch.setattr(worker, "Session", session)
    monkeypatch.setattr(worker, "Telegram", lambda kind: telegram)
    monkeypatch.setattr(worker.time, "sleep", lambda s: None)
    continued = []
    monkeypatch.setattr(queue, "task", lambda name, *args, countdown=0: continued.append(name))
    return telegram, continued


def test_worker_sends_in_batches_once_and_deletes(db, monkeypatch):
    people(db)
    telegram, continued = fake_worker(db, monkeypatch)
    b = Broadcast(text="<b>hi</b>", button_text="Open", button_url="https://x.example", bots=["media", "video"],
                  skip_premium=True, audience=3, created_by="x", photo_ids={})
    db.add(b)
    db.commit()
    blocked = {3}
    def call(method, data, files=None):
        if data["chat_id"] in blocked:
            raise TelegramError("Forbidden: bot was blocked by the user")
        return {"message_id": 100 + data["chat_id"]}
    telegram.call.side_effect = call
    worker.send(b.id)
    assert continued == [worker.SEND_TASK]  # one batch done, next batch queued
    worker.send(b.id)  # a redelivered or next run sends nobody twice
    assert db.get(Broadcast, b.id).status == "sent"
    assert telegram.call.call_count == 3
    sent = telegram.call.call_args_list[0].args[1]
    assert sent["parse_mode"] == "HTML" and sent["reply_markup"] == {"inline_keyboard": [[{"text": "Open", "url": "https://x.example"}]]}
    assert broadcasts.counts(db, b) == {"delivered": 2, "failed": 1, "processed": 3, "deleted": 0, "not_deleted": 0}

    b.status = "deleting"
    db.commit()
    telegram.delete.side_effect = lambda chat, message: chat == 1 or (_ for _ in ()).throw(TelegramError("message can't be deleted"))
    worker.delete(b.id)
    worker.delete(b.id)
    assert db.get(Broadcast, b.id).status == "deleted"
    assert broadcasts.counts(db, b)["deleted"] == 1 and broadcasts.counts(db, b)["not_deleted"] == 1


def test_deleting_stops_a_post_that_is_still_sending(db, monkeypatch):
    people(db)
    telegram, _ = fake_worker(db, monkeypatch)
    b = Broadcast(text="hi", bots=["media"], skip_premium=False, audience=3, created_by="x", photo_ids={})
    db.add(b)
    db.commit()
    def call(method, data, files=None):
        b.status = "deleting"  # the administrator pressed Delete after the first message
        db.commit()
        return {"message_id": 1}
    telegram.call.side_effect = call
    worker.send(b.id)
    assert db.scalar(select(func.count()).select_from(BroadcastMessage)) == 1


def test_photo_is_uploaded_once_per_bot(db, monkeypatch):
    people(db)
    telegram, _ = fake_worker(db, monkeypatch)
    telegram.call.side_effect = lambda method, data, files=None: {"message_id": 1, "photo": [{"file_id": "small"}, {"file_id": "big"}]}
    b = Broadcast(text="hi", photo=b"\xff\xd8\xffjpeg", bots=["media"], skip_premium=False, audience=3, created_by="x", photo_ids={})
    db.add(b)
    db.commit()
    worker.send(b.id)
    uploads = [c for c in telegram.call.call_args_list if c.kwargs.get("files")]
    assert len(uploads) == 1 and db.get(Broadcast, b.id).photo_ids == {"media": "big"}
    assert telegram.call.call_args_list[-1].args[1]["photo"] == "big"


def test_admin_publishes_tests_and_deletes(admin_client, db, monkeypatch):
    people(db)
    started = []
    monkeypatch.setattr(queue, "task", lambda name, *args, countdown=0: started.append((name, args)))
    form = {"text": "<b>Hello</b><script>x</script>", "bots": "media,video", "skip_premium": "true", "button_text": "", "button_url": ""}
    created = admin_client.post("/api/admin/broadcasts", data=form).json()
    assert created["text"] == "<b>Hello</b>x" and created["audience"] == 3 and created["status"] == "sending"
    assert started == [(worker.SEND_TASK, (created["id"],))]
    assert admin_client.post("/api/admin/broadcasts", data={**form, "bots": "nope"}).status_code == 400
    assert admin_client.post("/api/admin/broadcasts", data=form, files={"photo": ("x.gif", b"GIF89a", "image/gif")}).status_code == 400
    listing = admin_client.get("/api/admin/broadcasts").json()
    assert listing["bots"] == ["files", "media", "video"] and listing["items"][0]["deletable"]
    assert admin_client.get("/api/admin/broadcasts/audience?bots=media&skip_premium=false").json()["total"] == 3

    sent = MagicMock()
    sent.__enter__ = lambda self: self
    sent.__exit__ = lambda self, *a: None
    from backend.api import broadcasts as api
    monkeypatch.setattr(api, "Telegram", lambda kind: sent)
    assert admin_client.post("/api/admin/broadcasts/test", data={**form, "chat_id": "42"}).json() == {"ok": True, "bot": "media"}
    assert sent.call.call_args.args[1]["chat_id"] == 42

    removed = admin_client.post(f"/api/admin/broadcasts/{created['id']}/delete").json()
    assert removed["status"] == "deleting" and started[-1] == (worker.DELETE_TASK, (created["id"],))
    old = db.get(Broadcast, created["id"])
    old.created_at = now() - timedelta(hours=49)
    db.commit()
    assert admin_client.get("/api/admin/broadcasts").json()["items"][0]["deletable"] is False
