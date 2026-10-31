from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import MagicMock
import fakeredis
from sqlalchemy import func, select
from backend.config import settings
from backend.models import Job, Payment, User, Usage, now
from backend.services import monetization, queue, users
from workers import tasks

FORMATS = [{"selector": "18", "kind": "video", "height": 360, "size": 5_000_000, "label": "MP4 · 360p"},
           {"selector": "137+140", "kind": "video", "height": 1080, "size": 50_000_000, "label": "MP4 · 1080p"},
           {"selector": "big", "kind": "video", "height": 480, "size": 900_000_000, "label": "MP4 · 480p"}]


def headers(kind="video"):
    return {"X-Bot-Kind": kind, "X-Service-Key": settings().service_key(kind)}


def configure(db, **values):
    return monetization.save(db, monetization.Settings(**values))


def card_job(db, user_id=1):
    users.register(db, "video", user_id)
    meta = Job(user_id=user_id, bot_id="video", request_key=f"meta{user_id}", kind="metadata", platform="archive",
               source_url="https://archive.org/details/test", status="completed", result={"title": "T", "formats": FORMATS})
    db.add(meta)
    db.commit()
    return meta


def test_stars_purchase_checks_the_plan_and_activates_once(client, db):
    configure(db, premium_enabled=True, plans=[{"days": 30, "stars": 100}])
    users.register(db, "media", 7)
    good = {"user_id": 7, "payload": "premium:30:100", "amount": 100}
    assert client.post("/internal/premium/checkout", headers=headers("media"), json=good).json()["days"] == 30
    # A tampered price or an unknown plan is refused before Telegram charges anything.
    assert client.post("/internal/premium/checkout", headers=headers("media"), json={**good, "amount": 1}).status_code == 400
    assert client.post("/internal/premium/checkout", headers=headers("media"), json={**good, "payload": "premium:365:100"}).status_code == 400
    paid = {**good, "charge_id": "charge-1"}
    first = client.post("/internal/premium/activate", headers=headers("media"), json=paid).json()
    again = client.post("/internal/premium/activate", headers=headers("media"), json=paid).json()  # Telegram retry
    assert first["premium_until"] == again["premium_until"] and first["money"]["premium"]
    assert db.scalar(select(func.count()).select_from(Payment)) == 1
    payment = db.scalar(select(Payment))
    assert (payment.source, payment.stars, payment.days, payment.bot_id) == ("stars", 100, 30, "media")
    # A second purchase extends from the current end date instead of restarting it.
    client.post("/internal/premium/activate", headers=headers("media"), json={**paid, "charge_id": "charge-2"})
    assert db.get(User, 7).premium_until.date() >= (now() + timedelta(days=59)).date()


def test_free_users_get_hd_and_big_files_with_premium_only(client, db):
    configure(db, premium_enabled=True, free_max_height=720, free_max_mb=200)
    meta = card_job(db)
    pick = lambda index: client.post("/internal/download", headers=headers(), json={"user_id": 1, "metadata_id": meta.id, "index": index})
    assert pick(0).status_code == 200
    assert pick(1).json()["detail"] == "premium_quality" and pick(1).status_code == 402
    assert pick(2).json()["detail"] == "premium_size"
    monetization.grant(db, db.get(User, 1), 30, "admin")
    assert pick(1).status_code == 200 and pick(2).status_code == 200
    assert monetization.locked_formats(db, None, FORMATS) == {1, 2}


def test_premium_skips_the_daily_limit_and_jumps_the_queue(client, db, monkeypatch):
    configure(db, premium_enabled=True, free_max_height=0, free_max_mb=0)
    meta = card_job(db)
    db.get(User, 1).daily_limit = 1
    db.commit()
    sent = []
    monkeypatch.setattr(queue, "enqueue", lambda job_id, priority=False: sent.append(priority))
    pick = lambda index: client.post("/internal/download", headers=headers(), json={"user_id": 1, "metadata_id": meta.id, "index": index})
    assert pick(0).status_code == 200
    blocked = pick(1)
    assert blocked.status_code == 429 and blocked.json()["detail"] == "premium_limit"  # the bot answers with the Premium offer
    monetization.grant(db, db.get(User, 1), 30, "admin")
    assert pick(1).status_code == 200 and pick(2).status_code == 200
    assert sent == [False, True, True]


def test_invites_count_after_the_first_download_and_reward_every_n(client, db, monkeypatch):
    configure(db, referrals_enabled=True, referral_invites=2, referral_days=7)
    users.register(db, "media", 100)
    for friend in (201, 202):
        client.post("/internal/register", headers=headers("media"), json={"user_id": friend, "referrer": 100})
    client.post("/internal/register", headers=headers("media"), json={"user_id": 203, "referrer": 203})  # self-invite ignored
    client.post("/internal/register", headers=headers("media"), json={"user_id": 100, "referrer": 201})  # existing user ignored
    assert [db.get(User, i).referred_by for i in (201, 202, 203, 100)] == [100, 100, None, None]
    assert monetization.count_referral(db, 201) == {"referrer": 100, "count": 1, "needed": 2, "rewarded": False, "days": 7, "until": None}
    assert monetization.count_referral(db, 201) is None  # counted once
    reward = monetization.count_referral(db, 202)
    assert reward["rewarded"] and monetization.is_premium(db.get(User, 100))
    assert db.scalar(select(Payment.source)) == "referral"
    profile = client.post("/internal/register", headers=headers("media"), json={"user_id": 100}).json()["money"]
    assert profile["referrals"] == {"invites": 2, "days": 7, "count": 2} and profile["premium"]


def test_worker_shows_ads_to_free_users_and_tells_the_inviter(db, monkeypatch, tmp_path):
    @contextmanager
    def session():
        yield db
    monkeypatch.setattr(tasks, "Session", session)
    monkeypatch.setattr(tasks, "redis_client", lambda: fakeredis.FakeRedis())
    monkeypatch.setattr(tasks.cfg, "temp_root", str(tmp_path))
    monkeypatch.setattr(tasks.cfg, "min_free_disk_bytes", 0)
    telegram, adapter = MagicMock(), MagicMock()
    telegram.message.return_value = {"message_id": 10}
    monkeypatch.setattr(tasks, "Telegram", lambda _: telegram)
    monkeypatch.setattr(tasks, "MediaAdapter", lambda: adapter)
    configure(db, ads_enabled=True, ads=[{"text": "Try <Brand>", "button": "Open", "url": "https://example.com"}],
              referrals_enabled=True, referral_invites=3)
    users.register(db, "video", 50)
    users.register(db, "video", 42, referrer=50)
    job = Job(user_id=42, bot_id="video", request_key="ad", kind="download", platform="archive",
              source_url="https://archive.org/details/x", selected_format="18", payload={})
    db.add(job)
    db.flush()
    db.add(Usage(user_id=42, bot_id="video", job_id=job.id))
    db.commit()

    def download(url, selector, root, max_size, merge, on_progress=None, should_stop=None):
        (root / "v.mp4").write_bytes(b"x")
        return [root / "v.mp4"]
    adapter.download.side_effect = download
    monkeypatch.setattr(tasks.storage, "put_file", lambda db, job, path, days: MagicMock(id="f1", size=1, deleted=False, expires_at=now() + timedelta(days=1)))
    monkeypatch.setattr(tasks, "deliver", lambda *args: None)
    tasks.run(job.id)
    assert db.get(Job, job.id).status == "completed"
    status_text, buttons = telegram.message.call_args_list[0].args[1:3]
    assert "Sponsored" in status_text and "Try &lt;Brand&gt;" in status_text  # escaped, never raw HTML
    assert buttons[-1][0]["text"] == "Open" and f"/go/" in buttons[-1][0]["url"] and buttons[-1][0]["url"].endswith(job.id)
    assert telegram.message.call_args_list[-1].args[0] == 50  # the inviter hears about the friend
    assert "1 of 3" in telegram.message.call_args_list[-1].args[1]
    assert monetization.ad_views()


def test_no_ads_for_premium_and_same_ad_on_retry(db):
    configure(db, ads_enabled=True, ads=[{"text": "A"}, {"text": "B"}, {"text": "C"}])
    users.register(db, "media", 9)
    user = db.get(User, 9)
    assert monetization.pick_ad(db, user, "job-1") == monetization.pick_ad(db, user, "job-1")
    monetization.grant(db, user, 1, "admin")
    assert monetization.pick_ad(db, user, "job-1") is None


def test_ads_targeting_frequency_limit_and_click_counting(client, db, fake_infrastructure):
    configure(db, ads_enabled=True, ads_every=2, ads=[
        {"id": "yt-only", "text": "YouTube ad", "url": "https://shop.example/yt", "bots": ["video"]},
        {"id": "hebrew", "text": "Hebrew ad", "url": "https://shop.example/he", "languages": ["he"], "max_views": 1}])
    for user_id in (1, 2):
        users.register(db, "media", user_id)
    one, two = db.get(User, 1), db.get(User, 2)
    assert monetization.pick_ad(db, one, "j1", "media", "en") is None  # no ad matches the Media bot in English
    first = monetization.pick_ad(db, two, "j2", "video", "en")
    assert first["id"] == "yt-only" and first["url"].endswith("/go/yt-only/j2")  # the button counts clicks first
    assert monetization.pick_ad(db, two, "j3", "video", "en") is None  # every 2nd download of this user
    assert monetization.pick_ad(db, one, "j4", "media", "he")["id"] == "hebrew"
    assert monetization.pick_ad(db, one, "j6", "media", "he") is None  # view limit reached
    for _ in range(2):  # one click per download, however many times it is pressed
        response = client.get("/go/yt-only/j2", follow_redirects=False)
        assert response.status_code == 302 and response.headers["location"] == "https://shop.example/yt"
    assert client.get("/go/unknown/j2", follow_redirects=False).status_code == 404
    report = {a["id"]: a for a in monetization.ad_report(monetization.settings(db))}
    assert report["yt-only"]["views"] == 1 and report["yt-only"]["clicks"] == 1 and report["yt-only"]["ctr"] == 100.0
    assert report["yt-only"]["by_bot"] == {"video": 1}


def test_tiers_have_their_own_limits_and_credits_extend_the_daily_limit(client, db, monkeypatch):
    configure(db, premium_enabled=True, free_max_height=720, free_max_mb=0, tiers=[
        {"key": "premium", "name": "Premium"},
        {"key": "lite", "name": "Lite", "daily_jobs": 2, "max_height": 1080, "storage_mb": 1, "priority": False, "no_ads": False}],
        plans=[{"days": 30, "stars": 100}, {"tier": "lite", "days": 30, "stars": 40}],
        ads_enabled=True, ads=[{"id": "a1", "text": "Ad"}])
    m = monetization.settings(db)
    assert [p.key for p in m.plans] == ["30", "lite.30"]
    lite = monetization.paid_plan(monetization.invoice_payload(m.plan("lite.30")), 40)
    assert lite.tier == "lite" and lite.days == 30  # the tier travels in the Stars invoice
    meta = card_job(db)
    user = db.get(User, 1)
    monetization.grant(db, user, 30, "stars", tier="lite")
    assert monetization.tier_of(db, user).name == "Lite"
    assert monetization.format_lock(db, user, FORMATS[1]) is None  # 1080p is in Lite
    assert monetization.format_lock(db, user, {"kind": "video", "height": 2160}) == "premium_quality"
    assert monetization.pick_ad(db, user, "job-x", "video", "en")["id"] == "a1"  # Lite keeps the ads
    sent = []
    monkeypatch.setattr(queue, "enqueue", lambda job_id, priority=False: sent.append(priority))
    pick = lambda index: client.post("/internal/download", headers=headers(), json={"user_id": 1, "metadata_id": meta.id, "index": index})
    assert pick(0).status_code == 200 and pick(1).status_code == 200
    assert pick(2).status_code == 429  # Lite: 2 downloads a day
    user.credits = 1
    db.commit()
    assert pick(2).status_code == 200 and db.get(User, 1).credits == 0  # a credit buys one more
    assert sent == [False, False, False]  # Lite has no priority queue
    from backend.services import jobs
    with __import__("pytest").raises(Exception, match="storage_quota"):
        jobs.submit_upload(db, "files", 1, None, "big", "file-id", "report.pdf", 2_000_000)


def test_bots_and_tiers_choose_their_platforms(client, admin_client, db, monkeypatch):
    from backend.models import Bot
    monkeypatch.setattr("backend.services.jobs.normalize_url", lambda u: u)  # tests must not depend on DNS
    configure(db, free_platforms=["archive"], tiers=[{"key": "premium", "name": "Premium", "platforms": []}])
    users.register(db, "media", 5)
    submit = lambda url, key: client.post("/internal/metadata", headers=headers("media"),
                                          json={"user_id": 5, "url": url, "request_key": key})
    direct = "https://example.com/files/clip.mp4"
    assert submit(direct, "k1").json()["detail"] == "premium_feature"
    monetization.grant(db, db.get(User, 5), 30, "admin")
    assert submit(direct, "k2").status_code == 200  # Premium includes direct links
    admin_client.patch("/api/admin/bots/media", json={"enabled": True, "daily_limit": 1000, "platforms": ["archive", "wikimedia"]})
    assert db.get(Bot, "media").platforms == ["archive", "wikimedia"]
    assert submit(direct, "k3").json()["detail"] == "disabled"  # not in this bot
    assert admin_client.patch("/api/admin/bots/media", json={"enabled": True, "daily_limit": 1000, "platforms": ["myspace"]}).status_code == 400


def test_admin_configures_monetization_and_gifts_premium(admin_client, db):
    assert admin_client.get("/api/admin/monetization").json()["premium_enabled"] is False
    body = {**monetization.Settings().model_dump(), "premium_enabled": True, "channel_enabled": True, "channel": "https://t.me/my_channel",
            "ads_enabled": True, "ads": [{"text": "Hello", "url": "https://example.com"}]}
    saved = admin_client.put("/api/admin/monetization", json=body).json()
    assert saved["channel"] == "@my_channel" and saved["ads"][0]["id"]
    bad = admin_client.put("/api/admin/monetization", json={**body, "channel": "-1001234567", "channel_link": ""})
    assert bad.status_code == 422 and "invite link" in str(bad.json())
    assert admin_client.put("/api/admin/monetization", json={**body, "ads": [{"text": "x", "url": "javascript:alert(1)"}]}).status_code == 422
    users.register(db, "media", 5)
    assert admin_client.post("/api/admin/users/5/premium", json={"days": 10}).json()["premium_until"]
    stats = admin_client.get("/api/admin/monetization/stats").json()
    assert stats["premium_users"] == 1 and stats["recent"][0]["source"] == "admin" and "charge_id" not in stats["recent"][0]
    assert admin_client.post("/api/admin/users/5/premium", json={"days": 0}).json()["premium_until"] is None


def test_several_required_channels_reach_the_bots(admin_client, db):
    body = {**monetization.Settings().model_dump(), "channel_enabled": True, "channel": "@first_channel",
            "extra_channels": [{"chat": "https://t.me/second_channel"}, {"chat": "-1009876543210", "link": "https://t.me/+abc"},
                               {"chat": "@first_channel"}]}
    saved = admin_client.put("/api/admin/monetization", json=body).json()
    assert saved["extra_channels"][0]["chat"] == "@second_channel"
    channels = monetization.settings(db).required_channels()
    assert channels == [{"chat": "@first_channel", "url": "https://t.me/first_channel"},
                        {"chat": "@second_channel", "url": "https://t.me/second_channel"},
                        {"chat": "-1009876543210", "url": "https://t.me/+abc"}]  # the duplicate is dropped
    bad = admin_client.put("/api/admin/monetization", json={**body, "extra_channels": [{"chat": "-1001111111111"}]})
    assert bad.status_code == 422 and "invite link" in str(bad.json())
    user, _ = users.register(db, "media", 77)
    assert len(monetization.profile(db, user, 10, 0)["channels"]) == 3
