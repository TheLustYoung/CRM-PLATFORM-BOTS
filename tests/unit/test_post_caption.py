"""Delivered media: the clean video, the same file as a document, then the item's text with its author,
the file details (hidden download link) and the bot's name as a separate message."""
from types import SimpleNamespace
from workers.tasks import post_messages


def job(**payload):
    return SimpleNamespace(payload=payload)


def test_the_text_message_has_the_description_details_and_bot():
    messages = post_messages(job(title="Sunrise over the harbour", description="L’aube <sur le port> ✨\n\nArchive film, 1958"),
                             "mediabot", "✅ <b>a.mp4</b>")
    assert messages == ["L’aube &lt;sur le port&gt; ✨\n\nArchive film, 1958\n\n✅ <b>a.mp4</b>\n\n🤖 @mediabot"]
    assert post_messages(job(title="Only a title"), "b")[0].startswith("Only a title")
    assert post_messages(job(), "b") == ["🤖 @b"]


def test_a_long_post_continues_in_the_next_messages_and_entities_are_never_split():
    messages = post_messages(job(description="&" * 7000), "b", "details")
    assert len(messages) >= 2 and all(len(m) <= 4096 for m in messages)
    assert messages[-1].endswith("details\n\n🤖 @b") and "&amp;&amp;" in messages[0] and "&am\n" not in messages[0]


def test_file_links_hide_behind_a_download_word():
    from workers.tasks import hide_link, link_word
    url = "https://files.example.com/f/HKDVg6Ud?a=1&b=2"
    word = link_word("en", url)
    assert word == '<a href="https://files.example.com/f/HKDVg6Ud?a=1&amp;b=2">⬇ Download</a>'
    text = hide_link("✅ a.pdf\n🔗 https://files.example.com/f/HKDVg6Ud?a=1&amp;b=2\n⏳ until", "en", url)
    assert text.count("files.example.com") == 1 and word in text and link_word("en", None) == ""


def test_the_link_message_gets_a_reaction_when_the_media_is_delivered():
    from workers.tasks import link_message, react_done
    card = SimpleNamespace(request_key="msg:42:777")
    db = SimpleNamespace(get=lambda model, key: card if key == "card1" else None)
    download = SimpleNamespace(request_key="download:card1:0", user_id=42)
    assert link_message(db, download) == 777 and link_message(db, SimpleNamespace(request_key="other")) is None
    calls = []
    react_done(db, download, SimpleNamespace(call=lambda method, data: calls.append((method, data))))
    assert calls == [("setMessageReaction", {"chat_id": 42, "message_id": 777, "reaction": [{"type": "emoji", "emoji": "🫡"}]})]

    def broken(method, data):
        raise RuntimeError("reactions are off in this chat")
    react_done(db, download, SimpleNamespace(call=broken))  # never fails the job


def test_the_card_shows_the_description_and_still_fits_one_message():
    from workers.cards import card
    info = {"platform": "wikimedia", "title": "Harbour at dawn", "channel": "Example Author", "likes": 49, "license": "CC BY 4.0",
            "description": "L’aube se lève sur le port… ✨\n\nUne photographie <libre>.",
            "formats": [{"kind": "video", "ext": "mp4", "height": h, "label": f"{h}p"} for h in (1280, 960, 640)]}
    text, _ = card(info, "job1", "fr", "mediabot")
    assert "<blockquote expandable>L’aube se lève sur le port… ✨\n\nUne photographie &lt;libre&gt;.</blockquote>" in text
    long, _ = card({**info, "description": "mot " * 600}, "job1", "en", "mediabot")
    assert len(long) <= 1024 and "…</blockquote>" in long
    assert "blockquote" not in card({**info, "description": None}, "job1", "en", "b")[0]
