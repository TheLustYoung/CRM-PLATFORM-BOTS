from datetime import datetime, timedelta, timezone
from backend.models import Job
from backend.services import users


def test_overview_charts_come_from_real_jobs(admin_client, db):
    users.register(db, "media", 7)
    monday_9 = datetime(2026, 10, 26, 9, 15, tzinfo=timezone.utc)
    recent = datetime.now(timezone.utc) - timedelta(days=1)
    jobs = [("metadata", "completed", "wikimedia", recent), ("metadata", "completed", "archive", recent),
            ("download", "completed", "archive", recent), ("download", "failed", "archive", recent),
            ("upload", "completed", "telegram", recent), ("metadata", "completed", "direct", datetime.now(timezone.utc) - timedelta(days=40))]
    for n, (kind, status, platform, created) in enumerate(jobs):
        db.add(Job(user_id=7, bot_id="media", request_key=f"k{n}", kind=kind, status=status, platform=platform, created_at=created))
    db.commit()
    data = admin_client.get("/api/admin/overview").json()
    assert data["sources"] == {"wikimedia": 1, "archive": 1, "telegram": 1}  # the 40-day-old job is outside the window
    assert data["funnel"] == {"links": 2, "downloads": 2, "delivered": 1, "failed": 1}
    assert data["outcome"][recent.date().isoformat()] == {"completed": 1, "failed": 1}
    assert sum(map(sum, data["heatmap"])) == 5 and len(data["heatmap"]) == 7 and len(data["heatmap"][0]) == 24
    assert data["heatmap"][recent.weekday()][recent.hour] == 5 and monday_9.weekday() == 0
