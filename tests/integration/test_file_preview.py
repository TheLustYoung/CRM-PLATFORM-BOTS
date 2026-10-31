"""Dashboard "View" window: safe types are shown inline, everything else and the Download button are attachments."""
from datetime import timedelta
from backend.models import Job, UploadedFile, now
from backend.services import users
import storage


def add(db, name, mime, data=b"hello"):
    users.register(db, "files", 90)
    key = f"preview/{name}"
    db.add(Job(id=f"job-{name}", user_id=90, bot_id="files", request_key=name, kind="upload", status="completed"))
    file = UploadedFile(user_id=90, bot_id="files", job_id=f"job-{name}", name=name, mime=mime, size=len(data), object_key=key,
                        sha256="0" * 64, expires_at=now() + timedelta(days=1))
    db.add(file)
    db.commit()
    return file


def test_view_shows_safe_types_inline_and_downloads_the_rest(admin_client, db, monkeypatch):
    monkeypatch.setattr(storage, "open_object", lambda key: (iter([b"hello"]), lambda: None))
    photo = add(db, "a.png", "image/png")
    page = add(db, "b.html", "text/html")
    shown = admin_client.get(f"/api/admin/files/{photo.id}/content")
    assert shown.status_code == 200 and shown.headers["content-type"] == "image/png" and shown.headers["content-disposition"].startswith("inline")
    assert shown.content == b"hello" and "sandbox" in shown.headers["content-security-policy"]
    saved = admin_client.get(f"/api/admin/files/{photo.id}/content?download=1")
    assert saved.headers["content-disposition"].startswith("attachment") and saved.headers["content-type"] == "application/octet-stream"
    html = admin_client.get(f"/api/admin/files/{page.id}/content")
    assert html.headers["content-disposition"].startswith("attachment")  # uploaded HTML never renders in the dashboard
    assert admin_client.get("/api/admin/files/nope/content").status_code == 404


def test_job_view_shows_the_link_details_files_and_user_but_no_media_urls(admin_client, db):
    url = "https://www.instagram.com/reel/abc/"
    users.register(db, "media", 91)
    db.add(Job(id="card", user_id=91, bot_id="media", request_key="c", kind="metadata", source_url=url, platform="wikimedia",
               status="completed", result={"title": "Sunset", "channel": "@sky", "duration": 119, "formats": [{"url": "https://cdn/x.mp4"}],
                                            "thumbnail": "https://cdn/t.jpg"}))
    db.add(Job(id="dl", user_id=91, bot_id="media", request_key="d", kind="download", source_url=url, platform="wikimedia", status="completed"))
    db.add(UploadedFile(user_id=91, bot_id="media", job_id="dl", name="sunset.mp4", mime="video/mp4", size=10, object_key="k-dl",
                        sha256="0" * 64, expires_at=now() + timedelta(days=1)))
    db.commit()
    view = admin_client.get("/api/admin/jobs/dl").json()
    assert view["info"] == {"title": "Sunset", "channel": "@sky", "duration": 119} and view["user"]["id"] == 91
    assert [f["name"] for f in view["files"]] == ["sunset.mp4"] and "cdn" not in str(view)
    assert admin_client.get("/api/admin/jobs/missing").status_code == 404
