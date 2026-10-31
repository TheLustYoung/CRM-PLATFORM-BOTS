"""The bots' public channel from the dashboard: connect, publish now or later, edit, pin, delete."""
import json
from datetime import timedelta
import pytest
from backend.models import ChannelPost, now
from backend.services import channel


class FakeTelegram:
    calls: list = []
    fail: str | None = None

    def __init__(self, bot_id):
        self.bot_id = bot_id

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def call(self, method, data, files=None):
        from workers.telegram import TelegramError
        FakeTelegram.calls.append((method, data, sorted(files or {})))
        if FakeTelegram.fail and method == FakeTelegram.fail:
            raise TelegramError("Bad Request: not enough rights to send text messages to the chat")
        if method == "getChat":
            return {"title": "Demo channel", "username": "demo_channel", "type": "channel"}
        if method == "getChatMemberCount":
            return 1234
        if method == "getChatMember":
            return {"status": "administrator", "can_post_messages": True, "can_edit_messages": True, "can_delete_messages": True, "can_pin_messages": False}
        return {"message_id": 77}


@pytest.fixture
def tg(monkeypatch):
    FakeTelegram.calls, FakeTelegram.fail = [], None
    monkeypatch.setattr(channel, "telegram", FakeTelegram)
    monkeypatch.setattr("backend.api.channel.connected_bots", lambda db: ["media"])
    monkeypatch.setattr("backend.config.Settings.bot_token", lambda self, kind: "123456:" + "a" * 35)
    return FakeTelegram


def test_connect_publish_edit_pin_and_delete(admin_client, db, tg):
    assert admin_client.post("/api/admin/channel/posts", data={"text": "x"}).status_code == 400  # not connected yet
    saved = admin_client.put("/api/admin/channel", json={"chat": "https://t.me/demo_channel", "bot": "media"}).json()
    assert saved["settings"]["chat"] == "@demo_channel" and saved["channel"]["members"] == 1234
    assert saved["channel"]["rights"]["can_post_messages"] and not saved["channel"]["rights"]["can_pin_messages"]

    post = admin_client.post("/api/admin/channel/posts", data={"text": "<b>Hello</b> <script>x</script>",
                                                                "buttons": json.dumps([{"text": "Open bot", "url": "https://t.me/demo_bot"}])}).json()
    assert post["status"] == "published" and post["message_id"] == 77 and post["link"] == "https://t.me/demo_channel/77"
    method, data, _ = tg.calls[-1]
    assert method == "sendMessage" and data["chat_id"] == "@demo_channel" and data["text"] == "<b>Hello</b> x"
    assert data["reply_markup"] == {"inline_keyboard": [[{"text": "Open bot", "url": "https://t.me/demo_bot"}]]}

    edited = admin_client.post(f"/api/admin/channel/posts/{post['id']}/edit", data={"text": "Hello again", "buttons": "[]"}).json()
    assert edited["text"] == "Hello again" and tg.calls[-1][0] == "editMessageText" and tg.calls[-1][1]["reply_markup"] == {"inline_keyboard": []}
    assert admin_client.post(f"/api/admin/channel/posts/{post['id']}/pin", json={"pin": True}).json()["pinned"]
    assert tg.calls[-1][0] == "pinChatMessage"
    assert admin_client.post(f"/api/admin/channel/posts/{post['id']}/delete").json() == {"ok": True}
    assert tg.calls[-1][0] == "deleteMessage" and db.get(ChannelPost, post["id"]).status == "deleted"
    assert admin_client.get("/api/admin/channel").json()["posts"] == []


def test_scheduled_posts_go_out_when_their_time_comes(admin_client, db, tg):
    admin_client.put("/api/admin/channel", json={"chat": "@demo_channel", "bot": "media"})
    later = (now() + timedelta(hours=2)).isoformat()
    post = admin_client.post("/api/admin/channel/posts", data={"text": "Tomorrow's news", "publish_at": later}).json()
    assert post["status"] == "scheduled" and not any(c[0] == "sendMessage" for c in tg.calls)
    assert channel.publish_due(db) == 0
    row = db.get(ChannelPost, post["id"])
    row.publish_at = now() - timedelta(seconds=1)
    db.commit()
    assert channel.publish_due(db) == 1 and db.get(ChannelPost, post["id"]).status == "published"


def test_photo_posts_and_telegram_refusals(admin_client, db, tg):
    admin_client.put("/api/admin/channel", json={"chat": "-1001234567890", "bot": "media"})
    photo = b"\xff\xd8\xff" + b"0" * 100
    post = admin_client.post("/api/admin/channel/posts", data={"text": "With a photo"}, files={"media": ("a.jpg", photo, "image/jpeg")}).json()
    assert post["media_kind"] == "photo" and tg.calls[-1][0] == "sendPhoto" and tg.calls[-1][2] == ["photo"]
    assert admin_client.post("/api/admin/channel/posts", data={"text": "x"}, files={"media": ("a.exe", b"MZ" * 50, "application/octet-stream")}).status_code == 400
    assert admin_client.post("/api/admin/channel/posts", data={"text": "y" * 1100}, files={"media": ("a.jpg", photo, "image/jpeg")}).status_code == 400
    tg.fail = "sendMessage"
    failed = admin_client.post("/api/admin/channel/posts", data={"text": "No rights"}).json()
    assert failed["status"] == "failed" and "not enough rights" in failed["error"]
    tg.fail = None
    assert admin_client.post(f"/api/admin/channel/posts/{failed['id']}/publish").json()["status"] == "published"
    bad = admin_client.post("/api/admin/channel/posts", data={"text": "z", "buttons": json.dumps([{"text": "Go", "url": "javascript:alert(1)"}])})
    assert bad.status_code == 400


def test_all_bots_are_checked_and_the_first_allowed_one_posts(admin_client, db, tg, monkeypatch):
    monkeypatch.setattr("backend.api.channel.connected_bots", lambda db: ["files", "media", "video"])
    monkeypatch.setattr("backend.config.Settings.bot_token", lambda self, kind: {"files": "111:" + "a" * 35, "media": "222:" + "b" * 35, "video": "333:" + "c" * 35}[kind])
    real_call = FakeTelegram.call

    def call(self, method, data, files=None):
        if method == "getChatMember" and self.bot_id == "files":  # the File bot is not an administrator of the channel
            FakeTelegram.calls.append((method, data, []))
            return {"status": "member"}
        return real_call(self, method, data, files)
    monkeypatch.setattr(FakeTelegram, "call", call)
    saved = admin_client.put("/api/admin/channel", json={"chat": "@demo_channel", "bot": "all"}).json()
    info = saved["channel"]
    assert saved["settings"]["all"] and info["all_bots"] and info["posting_bot"] == "media"
    assert [(b["bot"], b["admin"]) for b in info["bots"]] == [("files", False), ("media", True), ("video", True)]
    post = admin_client.post("/api/admin/channel/posts", data={"text": "From all bots"}).json()
    assert post["status"] == "published" and post["bot"] == "media"
    assert admin_client.put("/api/admin/channel", json={"chat": "@demo_channel", "bot": "nope"}).status_code == 400
    ticked = admin_client.put("/api/admin/channel", json={"chat": "@demo_channel", "bots": ["video"]}).json()
    assert ticked["settings"] == {"chat": "@demo_channel", "bots": ["video"], "all": False}
    assert [b["chosen"] for b in ticked["channel"]["bots"]] == [False, False, True] and ticked["channel"]["posting_bot"] == "video"
    assert admin_client.put("/api/admin/channel", json={"chat": "@demo_channel", "bots": []}).status_code == 400  # nothing ticked
