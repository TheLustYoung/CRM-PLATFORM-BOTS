import pytest
from sqlalchemy import select
from backend.models import Audit
from backend.services import botprofile
from workers.telegram import TelegramError, TelegramRetry


class FakeTelegram:
    """In-memory Bot API: stores profile values per language like Telegram does."""
    state: dict = {}
    calls: list = []
    fail: Exception | None = None

    def __init__(self, kind):
        self.kind = kind

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def call(self, method, data, files=None):
        FakeTelegram.calls.append(method)
        if FakeTelegram.fail and method.startswith(("set", "remove")):
            raise FakeTelegram.fail
        lang = data.get("language_code") or ""
        store = FakeTelegram.state.setdefault((self.kind, lang), {"name": "", "short_description": "", "description": "", "commands": []})
        if method == "getMyName":
            return {"name": store["name"]}
        if method in {"getMyShortDescription", "getMyDescription"}:
            key = "short_description" if "Short" in method else "description"
            return {key: store[key]}
        if method == "getMyCommands":
            return store["commands"]
        if method == "setMyName":
            store["name"] = data["name"]
        elif method == "setMyShortDescription":
            store["short_description"] = data["short_description"]
        elif method == "setMyDescription":
            store["description"] = data["description"]
        elif method == "setMyCommands":
            store["commands"] = data["commands"]
        elif method == "setMyProfilePhoto":
            assert data["photo"] == {"type": "static", "photo": "attach://photo"} and files["photo"][2] == "image/jpeg"
        return True


@pytest.fixture
def telegram(monkeypatch):
    FakeTelegram.state, FakeTelegram.calls, FakeTelegram.fail = {}, [], None
    monkeypatch.setattr(botprofile, "Telegram", FakeTelegram)
    return FakeTelegram


def test_profile_per_language_and_only_changes_sent(admin_client, db, telegram):
    body = {"name": "Загрузчик", "short_description": "Скачивает видео", "description": "Пришлите ссылку",
            "commands": [{"command": "start", "description": "Начать"}]}
    saved = admin_client.put("/api/admin/bots/media/profile?lang=ar", json=body).json()
    assert saved["name"] == "Загрузчик" and saved["commands"][0]["command"] == "start"
    assert admin_client.get("/api/admin/bots/media/profile?lang=ar").json()["description"] == "Пришлите ссылку"
    assert admin_client.get("/api/admin/bots/media/profile").json()["name"] == ""  # default language untouched
    telegram.calls.clear()
    admin_client.put("/api/admin/bots/media/profile?lang=ar", json={**body, "description": "Новая"})
    assert "setMyName" not in telegram.calls and "setMyDescription" in telegram.calls  # setMyName is rate-limited
    assert db.scalar(select(Audit.target).where(Audit.action == "bot.profile")) == "media:ar"


def test_profile_validation(admin_client, telegram):
    assert admin_client.put("/api/admin/bots/media/profile", json={"commands": [{"command": "Bad Cmd", "description": "x"}]}).status_code == 422
    assert admin_client.put("/api/admin/bots/media/profile", json={"name": "x" * 65}).status_code == 422
    dup = [{"command": "a", "description": "x"}, {"command": "a", "description": "y"}]
    assert admin_client.put("/api/admin/bots/media/profile", json={"commands": dup}).status_code == 422
    assert admin_client.get("/api/admin/bots/media/profile?lang=xx").status_code == 400


def test_telegram_errors_reach_admin(admin_client, telegram):
    telegram.fail = TelegramRetry(retry_after=600)
    response = admin_client.put("/api/admin/bots/media/profile", json={"name": "New"})
    assert response.status_code == 429 and "600" in response.json()["detail"]
    telegram.fail = TelegramError("Bad Request: name is too long")
    assert admin_client.put("/api/admin/bots/media/profile", json={"name": "New"}).json()["detail"] == "Telegram: Bad Request: name is too long"


def test_photo_upload_type_and_audit(admin_client, db, telegram):
    jpeg = admin_client.post("/api/admin/bots/files/photo", files={"file": ("a.jpg", b"\xff\xd8\xff fake", "image/jpeg")})
    assert jpeg.status_code == 200 and "setMyProfilePhoto" in telegram.calls
    gif = admin_client.post("/api/admin/bots/files/photo", files={"file": ("a.gif", b"GIF89a", "image/gif")})
    assert gif.status_code == 400
    assert admin_client.delete("/api/admin/bots/files/photo").status_code == 200
    assert {a.action for a in db.scalars(select(Audit))} >= {"bot.photo", "bot.photo_remove"}


def test_profile_requires_admin(client):
    assert client.get("/api/admin/bots/media/profile").status_code == 401
