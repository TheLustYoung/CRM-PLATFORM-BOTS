from bots.common.media_flow import history_text
from bots.common.runner import button_texts, menu_keyboard


def test_menu_keyboard_per_bot_and_language():
    video = menu_keyboard("video", "en")
    assert [[b.text for b in row] for row in video.keyboard] == [["🕘 My downloads"], ["❓ Help", "🌐 Language"]]
    assert menu_keyboard("files", "en").keyboard[0][0].text == "📁 My files"
    assert video.resize_keyboard and video.is_persistent


def test_menu_buttons_match_in_every_language():
    assert {"❓ Help", "❓ مساعدة"} <= button_texts("menu_help")


def test_history_text_escapes_and_links():
    items = [{"title": "<Clip>", "label": "MP4 · 720p", "platform": "archive", "status": "completed",
              "created_at": "2026-10-16T10:00:00+00:00", "url": "https://files.example.com/f/abc"},
             {"title": "Post", "label": None, "platform": "wikimedia", "status": "failed",
              "created_at": "2026-10-15T10:00:00+00:00", "url": None}]
    text = history_text("en", items)
    assert "&lt;Clip&gt;" in text and 'href="https://files.example.com/f/abc"' in text
    assert "Internet Archive · MP4 · 720p · 2026-10-16" in text and "❌ <b>Post</b>" in text
    assert history_text("en", []).startswith("You haven't downloaded")
