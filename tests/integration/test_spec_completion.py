""" bot tokens, reports, translations, monitoring."""
from datetime import timedelta
from unittest.mock import MagicMock
import pytest
from backend.models import Bot, Job, Order, SystemSetting, UploadedFile, now
from backend.services import analytics, bot_tokens, i18n, translations, users


@pytest.fixture(autouse=True)
def clean_edits():
    i18n.set_edits({})
    yield
    i18n.set_edits({})


def test_translations_are_edited_in_the_dashboard_and_reach_every_text(admin_client, db):
    languages = admin_client.get("/api/admin/translations").json()
    assert {"code": "en", "fallback": True} .items() <= languages[0].items()
    texts = {t["key"]: t for t in admin_client.get("/api/admin/translations/he").json()}
    assert "login_required" in texts and texts["login_required"]["default"]
    saved = admin_client.put("/api/admin/translations/he", json={"texts": {"rate_limit": "⏳ <b>רגע</b>, נסו שוב"}})
    assert saved.status_code == 200 and saved.json()["edited"] == 1
    assert i18n.raw("he", "rate_limit") == "⏳ <b>רגע</b>, נסו שוב"
    bad = admin_client.put("/api/admin/translations/he", json={"texts": {"premium_status_free": "{secret} <script>"}})
    assert bad.status_code == 400 and bad.json()["detail"].startswith("bad_placeholder")
    assert admin_client.put("/api/admin/translations/he", json={"texts": {"rate_limit": "<i>open"}}).json()["detail"].startswith("bad_html")
    admin_client.put("/api/admin/translations/he", json={"texts": {"rate_limit": ""}})  # empty = the original again
    assert i18n.raw("he", "rate_limit") == i18n.catalogs()["he"]["rate_limit"]


def test_languages_can_be_switched_off_but_not_the_fallback(admin_client, db):
    assert admin_client.post("/api/admin/translations/bn/disable").status_code == 200
    assert "bn" not in i18n.languages() and i18n.resolve("bn-BD") == "en"
    assert admin_client.post("/api/admin/translations/en/disable").status_code == 400
    admin_client.post("/api/admin/translations/bn/enable")
    assert "bn" in i18n.languages()


def test_heartbeat_hands_the_edits_to_the_bots(client, db):
    from tests.integration.test_api import headers
    translations.save(db, "ru", {"rate_limit": "Подождите минуту"})
    beat = client.post("/internal/heartbeat", headers=headers("media"), json={"username": "mediabot"}).json()
    assert beat["translations"]["texts"]["ru"]["rate_limit"] == "Подождите минуту" and beat["token"]


def test_reports_by_period_bot_platform_with_errors_and_revenue(admin_client, db):
    users.register(db, "media", 1)
    users.register(db, "video", 2)
    day = now()
    for bot, platform, status, error in [("media", "instagram", "completed", None), ("media", "instagram", "failed", "unavailable"),
                                         ("video", "video", "completed", None)]:
        db.add(Job(user_id=1 if bot == "media" else 2, bot_id=bot, request_key=f"{bot}{status}", kind="download", platform=platform,
                   status=status, error=error, created_at=day, completed_at=day))
    db.add(Order(token="t" * 20, user_id=1, bot_id="media", days=30, method="stripe", currency="USD", amount=499, status="paid",
                 paid_at=day, expires_at=day))
    db.flush()
    db.add(UploadedFile(user_id=1, bot_id="files", job_id=db.query(Job.id).first()[0], name="a.pdf", mime="application/pdf", size=1234, object_key="k",
                        sha256="0" * 64, expires_at=day + timedelta(days=7)))
    db.commit()
    data = admin_client.get("/api/admin/analytics?period=week&count=4").json()
    last = data["series"][-1]
    assert len(data["series"]) == 4 and last["downloads"] == 3 and last["failed"] == 1 and last["error_rate"] == 33.3
    assert last["active_users"] == 2 and last["revenue"] == {"stripe:USD": 499}
    assert data["by_bot"] == {"media": 2, "video": 1} and data["by_platform"]["instagram"] == 2
    assert data["errors"] == {"unavailable": 1} and data["storage"]["bytes"] == 1234
    only_media = admin_client.get("/api/admin/analytics?period=month&count=1&bot=media").json()
    assert only_media["series"][0]["downloads"] == 2
    csv = admin_client.get("/api/admin/analytics.csv?period=day&count=2")
    assert csv.status_code == 200 and csv.text.splitlines()[0].startswith("period,downloads") and "revenue_stripe:USD" in csv.text


def test_monitoring_finds_problems_and_alerts_once_an_hour(admin_client, db, monkeypatch, fake_infrastructure):
    from workers import monitor
    db.add(SystemSetting(key=monitor.SETTINGS_KEY, value={"chat_id": "-100123", "disk_min_gb": 10 ** 6}))
    bot = db.get(Bot, "media")
    bot.last_seen = now() - timedelta(hours=1)
    db.commit()
    monkeypatch.setattr(monitor.settings(), "media_bot_token", type(monitor.settings().media_bot_token)("1:" + "a" * 35))
    status = monitor.measure(db)
    kinds = {p["kind"] for p in status["problems"]}
    assert {"disk", "bots"} <= kinds and "media" in status["silent_bots"]
    telegram = MagicMock()
    monkeypatch.setattr("workers.telegram.Telegram", lambda kind: telegram)
    telegram.__enter__ = lambda self: telegram
    telegram.__exit__ = lambda self, *a: None

    class Scope:
        def __enter__(self): return db
        def __exit__(self, *a): return False
    monkeypatch.setattr(monitor, "Session", Scope)
    monitor.check()
    first = telegram.message.call_count
    monitor.check()
    assert first >= 2 and telegram.message.call_count == first  # the same problems are not repeated within the hour
    page = admin_client.get("/api/admin/monitoring").json()
    assert page["settings"]["chat_id"] == "-100123" and page["status"]["problems"]


def test_user_card_shows_payments_files_can_be_permanent_and_referrals_give_credits(admin_client, db, client):
    from backend.models import User
    from backend.services import monetization
    monetization.save(db, monetization.Settings(referrals_enabled=True, referral_invites=1, referral_days=3, referral_credits=5))
    users.register(db, "media", 70)
    users.register(db, "media", 71, referrer=70)
    assert monetization.count_referral(db, 71)["rewarded"]
    assert db.get(User, 70).credits == 5 and monetization.is_premium(db.get(User, 70))
    card = admin_client.get("/api/admin/users/70").json()
    assert card["payments"][0]["source"] == "referral" and card["payments"][0]["days"] == 3 and card["tier"] == "Premium"
    db.add(Job(id="file-job", user_id=70, bot_id="files", request_key="f", kind="upload", status="completed"))
    file = UploadedFile(user_id=70, bot_id="files", job_id="file-job", name="a.pdf", mime="application/pdf", size=10,
                        object_key="k2", sha256="0" * 64, expires_at=now() + timedelta(days=1))
    db.add(file)
    db.commit()
    kept = admin_client.post(f"/api/admin/files/{file.id}/keep", json={"days": 0}).json()
    assert kept["permanent"] and kept["expires_at"].startswith("2100")


def test_alerts_also_go_by_email_and_the_key_is_never_shown(admin_client, db, monkeypatch):
    from workers import monitor
    saved = admin_client.put("/api/admin/monitoring", json={"email_to": "ops@example.com, boss@example.com", "email_from": "alerts@example.com",
                                                             "email_provider": "resend", "email_key": "re_secret_key_123"}).json()
    assert saved["settings"]["email_key_set"] and "re_secret_key_123" not in str(saved)
    again = admin_client.put("/api/admin/monitoring", json={**{k: v for k, v in saved["settings"].items() if k != "email_key_set"}, "email_key": ""})
    assert again.json()["settings"]["email_key_set"]  # an empty field keeps the saved key
    sent = []

    class Http:
        def __init__(self, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def post(self, url, json, headers):
            sent.append((url, json, headers["Authorization"]))
            return type("R", (), {"status_code": 200})()
    monkeypatch.setattr("httpx.Client", Http)
    assert monitor.alert(db, "Low disk space")
    url, body, auth = sent[0]
    assert url == monitor.EMAIL_PROVIDERS["resend"] and body["to"] == ["ops@example.com", "boss@example.com"]
    assert auth == "Bearer re_secret_key_123" and body["text"] == "Low disk space"
    assert admin_client.put("/api/admin/monitoring", json={"email_to": "not an address"}).status_code == 422


def test_error_reports_never_contain_bot_tokens():
    from backend import observability
    event = {"message": "failed for 123456789:" + "A" * 35, "extra": {"url": ["https://api.telegram.org/bot987654321:" + "b" * 35 + "/getMe"]}}
    clean = observability._scrub(event, None)
    assert "AAAA" not in str(clean) and "bbbb" not in str(clean) and "[token]" in clean["message"]
    assert observability.setup("test") is False  # no SENTRY_DSN: nothing is started


def test_bot_tokens_are_checked_stored_encrypted_and_never_returned(admin_client, db, monkeypatch):
    monkeypatch.setattr(bot_tokens, "check", lambda token: {"id": 1, "username": "newmediabot"})
    token = "123456789:" + "A" * 35
    saved = admin_client.put("/api/admin/bots/media/token", json={"token": token}).json()
    assert saved == {"source": "dashboard", "username": "newmediabot"}
    row = db.get(SystemSetting, "bot_token:media")
    assert token not in str(row.value) and bot_tokens.stored(db, "media") == token
    assert token not in admin_client.get("/api/admin/bots/media/token").text
    assert admin_client.delete("/api/admin/bots/media/token").json()["source"] in ("env", "none")
    monkeypatch.undo()
    assert admin_client.put("/api/admin/bots/media/token", json={"token": "not-a-token"}).status_code == 400


def test_downloaded_media_and_uploaded_files_have_their_own_retention(admin_client, db):
    from backend.services.limits import policy
    db.merge(SystemSetting(key="policy", value={**policy(db).model_dump(exclude={"media_retention_days"}), "retention_days": 30}))
    db.commit()
    assert policy(db).media_retention_days == 30  # saved before the split: media keeps the old period
    body = {k: v for k, v in admin_client.get("/api/admin/settings").json().items() if k != "languages"}
    saved = admin_client.patch("/api/admin/settings", json={**body, "media_retention_days": 3}).json()
    assert saved["media_retention_days"] == 3 and saved["retention_days"] == 30
    assert admin_client.patch("/api/admin/settings", json={**body, "media_retention_days": 0}).status_code == 422
