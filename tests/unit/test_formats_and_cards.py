from workers.adapters import build_formats
from workers.cards import card, duration, human_size

SAMPLE_FORMATS = [
    {"format_id": "sb0", "url": "u", "ext": "mhtml", "vcodec": "none", "acodec": "none"},
    {"format_id": "139", "url": "u", "ext": "m4a", "vcodec": "none", "acodec": "mp4a", "abr": 48.8, "filesize": 500},
    {"format_id": "140", "url": "u", "ext": "m4a", "vcodec": "none", "acodec": "mp4a", "abr": 129.5, "filesize": 2000},
    {"format_id": "251", "url": "u", "ext": "webm", "vcodec": "none", "acodec": "opus", "abr": 135.0, "filesize": 2100},
    {"format_id": "18", "url": "u", "ext": "mp4", "vcodec": "avc1", "acodec": "mp4a", "height": 360, "tbr": 500, "filesize": 9000},
    {"format_id": "134", "url": "u", "ext": "mp4", "vcodec": "avc1", "acodec": "none", "height": 360, "tbr": 300, "filesize": 7000},
    {"format_id": "137", "url": "u", "ext": "mp4", "vcodec": "avc1", "acodec": "none", "height": 1080, "tbr": 4000, "filesize": 50000},
    {"format_id": "248", "url": "u", "ext": "webm", "vcodec": "vp9", "acodec": "none", "height": 1080, "tbr": 3000},
    {"format_id": "drm", "url": "u", "ext": "mp4", "vcodec": "avc1", "acodec": "none", "height": 2160, "has_drm": True},
    {"format_id": "bad id;rm", "url": "u", "ext": "mp4", "vcodec": "avc1", "acodec": "mp4a", "height": 720},
]


def test_formats_are_real_grouped_and_merged():
    formats = build_formats(SAMPLE_FORMATS)
    video = [f for f in formats if f["kind"] == "video"]
    audio = [f for f in formats if f["kind"] == "audio"]
    assert [f["label"] for f in video] == ["MP4 · 1080p", "WEBM · 1080p", "MP4 · 360p"]
    assert video[0]["selector"] == "137+140" and video[0]["merge"] == "mp4" and video[0]["size"] == 52000
    assert video[1]["selector"] == "248+251" and video[1]["size"] is None  # unknown size is not invented
    assert video[2]["selector"] == "18"  # progressive stream preferred by bitrate
    assert [f["label"] for f in audio] == ["WEBM · 135 kbps", "M4A · 130 kbps", "M4A · 49 kbps"]
    assert all("2160" not in f["label"] for f in formats)  # DRM excluded


def test_card_lists_formats_licence_and_omits_missing_stats():
    info = {"platform": "archive", "title": "<Title>", "channel": "Chan", "duration": 3725, "views": 1234567, "likes": None,
            "comments": 12, "date": "20240501", "license": "Public Domain", "formats": build_formats(SAMPLE_FORMATS)}
    text, buttons = card(info, "job-1", "en", "MyBot")
    assert "&lt;Title&gt;" in text and "1:02:05" in text and "1,234,567" in text and "2024-05-01" in text
    assert "Platform: Internet Archive" in text and "Licence: Public Domain" in text
    assert "Likes" not in text and "Comments: 12" in text  # an unknown number is left out, never a fake 0
    assert "Video formats" in text and "MP4 · 1080p · ≈ 52.0 KB" in text and "Audio formats" in text
    assert text.endswith("@MyBot")
    flat = [b for row in buttons for b in row]
    assert flat[0]["callback_data"] == "dl:job-1:0"
    assert {"rf:job-1", "in:job-1"} <= {b["callback_data"] for b in flat}
    assert all(len(b["callback_data"]) <= 64 and len(b["text"]) <= 64 for b in flat)


def test_arabic_card_is_rtl_and_marks_a_missing_licence():
    text, _ = card({"platform": "wikimedia", "title": "Photo", "formats": []}, "j", "ar", "bot")
    assert text.startswith("‏") and "Wikimedia Commons" in text
    assert "الترخيص" in text and "غير متاح" in text  # a library item without licence data says so openly
    direct, _ = card({"platform": "direct", "title": "clip.mp4", "formats": []}, "j", "en", "bot")
    assert "Licence" not in direct  # a direct file link has no licence page


def test_size_estimated_from_bitrate_when_missing():
    video = [f for f in build_formats(SAMPLE_FORMATS, duration=10) if f["kind"] == "video"]
    assert video[1]["label"] == "WEBM · 1080p" and video[1]["size"] == 3000 * 125 * 10 + 2100


def test_buttons_are_compact():
    from workers.cards import button_text
    assert button_text({"kind": "video", "ext": "webm", "height": 2160, "size": 310_800_000}, "en") == "🎞 2160p webm · 311M"
    assert button_text({"kind": "audio", "ext": "m4a", "abr": 130, "size": 2_200_000}, "en") == "🎧 m4a 130k · 2.2M"
    assert button_text({"kind": "audio", "ext": "webm", "abr": 51, "size": 859_200}, "en") == "🎧 webm 51k · 859K"


def test_helpers():
    assert duration(59) == "0:59" and duration(None) is None
    assert human_size(1_500_000) == "1.5 MB" and human_size(None) is None
