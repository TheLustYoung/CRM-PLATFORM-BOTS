from datetime import timedelta
from moto import mock_aws
from sqlalchemy import select, func
from backend.config import settings
from backend.models import User, Job, UploadedFile, PublicLink, Usage, Audit, now
from backend.services import users
import storage


def headers(kind="video"):
    return {"X-Bot-Kind": kind, "X-Service-Key": settings().service_key(kind)}


def test_admin_and_internal_require_authentication(client):
    assert client.get("/api/admin/overview").status_code == 401
    assert client.post("/internal/register", json={"user_id": 1}).status_code == 401
    assert client.post("/internal/register", headers={**headers(), "X-Service-Key": "wrong"}, json={"user_id": 1}).status_code == 401


def test_login_origin_and_password(admin_client):
    assert admin_client.post("/api/auth/login", json={"username": "operator", "password": "incorrect"}).status_code == 401
    assert admin_client.patch("/api/admin/users/1", headers={"Origin": "https://attacker.invalid"}, json={"banned": True}).status_code == 403


def test_register_detects_telegram_language_and_is_shared(client, db):
    first = client.post("/internal/register", headers=headers(), json={"user_id": 100, "language_code": "ar-SA", "first_name": "علي"}).json()
    assert first["created"] and first["language"] == "ar"
    assert set(first["languages"]) >= {"en", "ar"}
    other_bot = client.post("/internal/register", headers=headers("media"), json={"user_id": 100}).json()
    assert other_bot["language"] == "ar" and not other_bot["created"]
    assert client.post("/internal/language", headers=headers("files"), json={"user_id": 100, "language": "en"}).status_code == 200
    assert client.post("/internal/register", headers=headers(), json={"user_id": 100}).json()["language"] == "en"
    assert client.post("/internal/language", headers=headers(), json={"user_id": 100, "language": "xx"}).status_code == 422
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_unknown_telegram_language_falls_back(client):
    assert client.post("/internal/register", headers=headers(), json={"user_id": 5, "language_code": "zz"}).json()["language"] == "en"


def test_ban_and_disabled_bot(admin_client, db):
    admin_client.post("/internal/register", headers=headers(), json={"user_id": 1})
    assert admin_client.patch("/api/admin/users/1", json={"banned": True}).status_code == 200
    assert admin_client.post("/internal/register", headers=headers(), json={"user_id": 1}).json()["detail"] == "banned"
    assert admin_client.patch("/api/admin/bots/media", json={"enabled": False, "daily_limit": 100, "welcome_text": "Hi"}).status_code == 200
    assert admin_client.post("/internal/register", headers=headers("media"), json={"user_id": 2}).json()["detail"] == "disabled"
    assert {a.action for a in db.scalars(select(Audit))} == {"user.ban", "bot.update"}


def test_metadata_routing_by_bot(client, db, fake_infrastructure):
    body = {"user_id": 7, "request_key": "m1", "url": "https://archive.org/details/BaW_jenozKc"}
    # Resolution is skipped: tests must not depend on DNS.
    from unittest.mock import patch
    with patch("backend.services.jobs.normalize_url", side_effect=lambda u: u):
        first = client.post("/internal/metadata", headers=headers(), json=body).json()
        again = client.post("/internal/metadata", headers=headers(), json=body).json()
        assert first["created"] and not again["created"] and first["id"] == again["id"]
        assert fake_infrastructure == [first["id"]]
        assert db.scalar(select(func.count()).select_from(Usage)) == 0  # viewing formats does not use the daily limit
        direct = "https://cdn.example.org/a/clip.mp4"
        assert client.post("/internal/metadata", headers=headers(), json={**body, "request_key": "m2", "url": direct}).json()["detail"] == "unsupported"
        assert client.post("/internal/metadata", headers=headers("media"), json={**body, "request_key": "m3", "url": direct}).status_code == 200
        assert client.post("/internal/metadata", headers=headers("media"), json={**body, "request_key": "m5", "url": "https://vimeo.com/1"}).json()["detail"] == "unsupported"
        assert client.post("/internal/metadata", headers=headers("files"), json=body).json()["detail"] == "unsupported"
    assert client.post("/internal/metadata", headers=headers(), json={**body, "request_key": "m4", "url": "http://127.0.0.1/x"}).json()["detail"] == "invalid_url"


def test_download_dedup_and_callback_owner(client, db):
    users.register(db, "video", 1)
    meta = Job(user_id=1, bot_id="video", request_key="meta", kind="metadata", source_url="https://archive.org/details/test",
               platform="archive", status="completed", result={"title": "T", "formats": [{"selector": "137+140", "merge": "mp4", "kind": "video", "label": "MP4 · 1080p"}]})
    db.add(meta)
    db.commit()
    body = {"user_id": 1, "metadata_id": meta.id, "index": 0}
    first = client.post("/internal/download", headers=headers(), json=body).json()
    again = client.post("/internal/download", headers=headers(), json=body).json()
    assert first["id"] == again["id"] and first["created"] and not again["created"]
    job = db.get(Job, first["id"])
    assert job.selected_format == "137+140" and job.payload["merge"] == "mp4" and job.payload["title"] == "T"
    assert db.scalar(select(func.count()).select_from(Usage)) == 1
    assert client.post("/internal/download", headers=headers(), json={**body, "user_id": 2}).status_code == 404
    assert client.post("/internal/download", headers=headers("media"), json=body).status_code == 404
    assert client.post("/internal/download", headers=headers(), json={**body, "index": 5}).json()["detail"] == "unsupported"
    info = client.post(f"/internal/jobs/{meta.id}/info", headers=headers(), json={"user_id": 1}).json()
    assert info["title"] == "T" and info["url"] == meta.source_url
    assert client.post(f"/internal/jobs/{meta.id}/info", headers=headers(), json={"user_id": 2}).status_code == 404


def test_history_lists_own_downloads_only(client, db):
    users.register(db, "media", 1)
    users.register(db, "media", 2)
    db.add_all([Job(user_id=1, bot_id="media", request_key="d1", kind="download", status="completed", platform="archive",
                    source_url="https://archive.org/details/a", payload={"title": "Clip", "label": "MP4 · 720p"}),
                Job(user_id=1, bot_id="media", request_key="m1", kind="metadata", status="completed", platform="archive"),
                Job(user_id=2, bot_id="media", request_key="d2", kind="download", status="failed", platform="direct")])
    db.commit()
    items = client.post("/internal/history", headers=headers("media"), json={"user_id": 1}).json()
    assert [(i["title"], i["label"], i["status"]) for i in items] == [("Clip", "MP4 · 720p", "completed")]
    assert client.post("/internal/history", headers=headers("video"), json={"user_id": 1}).json() == []


def test_upload_limits_and_policy_effect(admin_client):
    policy = admin_client.get("/api/admin/settings").json()
    assert "ar" in policy.pop("languages")
    policy["max_upload_bytes"] = 1024
    assert admin_client.patch("/api/admin/settings", json=policy).status_code == 200
    body = {"user_id": 1, "request_key": "message:1", "file_id": "telegram-id", "name": "report.pdf", "size": 2048}
    assert admin_client.post("/internal/upload", headers=headers("files"), json=body).json()["detail"] == "file_size"
    assert admin_client.post("/internal/upload", headers=headers("files"), json={**body, "size": 100, "name": "evil.exe"}).json()["detail"] == "file_type"
    assert admin_client.post("/internal/upload", headers=headers("files"), json={**body, "size": 100, "name": "تقرير.pdf"}).status_code == 200
    assert admin_client.patch("/api/admin/settings", json={**policy, "default_language": "xx"}).status_code == 422


def test_daily_limit(client, db):
    users.register(db, "files", 1)
    db.get(User, 1).daily_limit = 1
    db.commit()
    body = {"user_id": 1, "request_key": "a", "file_id": "id", "name": "a.pdf", "size": 100}
    assert client.post("/internal/upload", headers=headers("files"), json=body).status_code == 200
    assert client.post("/internal/upload", headers=headers("files"), json={**body, "request_key": "b"}).status_code == 429


def test_public_link_page_download_revoke_expire_delete(admin_client, db, tmp_path):
    users.register(db, "files", 1)
    job = Job(user_id=1, bot_id="files", request_key="a", kind="upload")
    db.add(job)
    db.commit()
    path = tmp_path / "отчёт.txt"
    path.write_bytes(b"real file bytes")
    with mock_aws():
        storage.ensure_bucket()
        file = storage.put_file(db, job, path, 1)
        assert file.sha256 and file.mime == "text/plain" and file.bot_id == "files"
        token = db.scalar(select(PublicLink.token).where(PublicLink.file_id == file.id))
        page = admin_client.get(f"/f/{token}", headers={"Accept-Language": "ar,en;q=0.5"})
        assert page.status_code == 200 and 'dir="rtl"' in page.text and "@files_test_bot" in page.text and "отчёт.txt" in page.text
        response = admin_client.get(f"/f/{token}/download")
        assert response.status_code == 200 and response.content == b"real file bytes"
        assert response.headers["content-type"] == "application/octet-stream" and "attachment" in response.headers["content-disposition"]
        assert db.get(UploadedFile, file.id).downloads == 1
        storage.delete_object(file.object_key)  # storage lost the object behind the platform's back
        missing = admin_client.get(f"/f/{token}/download", headers={"Accept-Language": "de"})  # unsupported language: English page
        assert missing.status_code == 404 and "no longer available" in missing.text
        assert db.get(UploadedFile, file.id).downloads == 1
        assert admin_client.post(f"/internal/files/{file.id}/revoke", headers=headers("files"), json={"user_id": 2}).status_code == 404
        mine = admin_client.post("/internal/files", headers=headers("files"), json={"user_id": 1}).json()
        assert mine[0]["url"].endswith(token)
        file.expires_at = now() - timedelta(seconds=1)
        db.commit()
        assert admin_client.get(f"/f/{token}").status_code == 404
        assert admin_client.get(f"/f/{token}/download").status_code == 404
        file.expires_at = now() + timedelta(days=1)
        db.commit()
        assert admin_client.post(f"/api/admin/files/{file.id}/revoke").status_code == 200
        assert admin_client.get(f"/f/{token}/download").status_code == 404
        assert admin_client.delete(f"/api/admin/files/{file.id}").status_code == 200
        assert db.get(UploadedFile, file.id).deleted


def test_overview_bots_users_audit(admin_client, db):
    assert admin_client.get("/api/admin/overview").json()["users"] == 0
    users.register(db, "video", 1, "alice")
    overview = admin_client.get("/api/admin/overview").json()
    assert overview["users"] == 1 and overview["active_users"] == 1
    bots = {b["id"]: b for b in admin_client.get("/api/admin/bots").json()}
    assert bots["video"]["users"] == 1 and bots["video"]["configured"]
    assert admin_client.get("/api/admin/users?q=@ali").json()[0]["username"] == "alice"
    assert admin_client.get("/api/admin/users/1").json()["bots"] == ["video"]
    admin_client.patch("/api/admin/users/1", json={"banned": False, "daily_limit": 5})
    assert admin_client.get("/api/admin/audit").json()[0]["admin"] == "operator"


def test_cancel_only_own_queued_job(client, db, fake_infrastructure):
    from backend.services import jobs as job_service, limits
    users.register(db, "video", 5)
    job = Job(user_id=5, bot_id="video", request_key="c", kind="download", source_url="https://archive.org/details/x", status="queued")
    db.add(job)
    db.flush()
    db.add(Usage(user_id=5, bot_id="video", job_id=job.id))
    db.commit()
    assert client.post(f"/internal/jobs/{job.id}/cancel", headers=headers(), json={"user_id": 6}).status_code == 404
    assert client.post(f"/internal/jobs/{job.id}/cancel", headers=headers(), json={"user_id": 5}).json()["status"] == "failed"
    db.refresh(job)
    assert job.error == "cancelled" and limits.redis_client().exists(job_service.CANCEL_KEY.format(job.id))
    assert db.scalar(select(func.count()).select_from(Usage).where(Usage.job_id == job.id)) == 0
