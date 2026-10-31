from bots.common.money import invite_link, premium_screen
from bots.common.runner import menu_keyboard, referrer_id
from workers.cards import card

PLAN = {"recurring": False, "title": "", "badge": "", "discount": 0, "stars_ok": True, "page": []}
MONEY = {"premium": False, "premium_until": None,
         "plans": [{**PLAN, "key": "30", "days": 30, "stars": 100}, {**PLAN, "key": "365", "days": 365, "stars": 900}],
         "used_today": 3, "daily_limit": 20, "free_max_height": 720, "free_max_mb": 200, "ads": True,
         "referrals": {"invites": 3, "days": 7, "count": 1}, "channel": None}


def test_invite_links_are_parsed_strictly():
    assert referrer_id("ref_12345") == 12345
    assert referrer_id(None) is None and referrer_id("ref_abc") is None and referrer_id("ref_1;drop") is None


def test_premium_screen_lists_status_benefits_plans_and_invite_link():
    link = invite_link("media_bot", 42)
    text, markup = premium_screen("en", MONEY, link)
    assert "3 of 20 downloads" in text and "up to 720p" in text and "up to 200 MB" in text and "No ads" in text
    assert link == "https://t.me/media_bot?start=ref_42" and link in text and "Friends counted: 1" in text
    rows = markup.inline_keyboard
    assert [r[0].callback_data for r in rows[:2]] == ["buy:30:100", "buy:365:900"]
    assert rows[0][0].text == "⭐ 30 days · 100 ⭐" and rows[-1][0].url.startswith("https://t.me/share/url?url=https%3A%2F%2Ft.me")
    active, _ = premium_screen("ar", {**MONEY, "premium": True, "premium_until": "2026-12-01T00:00:00+00:00", "ads": False}, link)
    assert "2026-12-01" in active and active.startswith("‏")  # right-to-left mark for Arabic


def test_plan_buttons_show_name_prices_discount_and_badge():
    from bots.common.money import payment_choice, plan_button
    sub = plan_button("en", {**PLAN, "key": "30r", "days": 30, "recurring": True, "stars": 80, "discount": 20, "badge": "🔥 Hit"})
    assert sub.text == "🔄 Every month · 80 ⭐/30d · -20% · 🔥 Hit" and sub.callback_data == "buy:30r:80"
    page = [{"key": "card", "label_key": "btn_pay_card", "amount": 199, "currency": "USD"},
            {"key": "crypto", "label_key": "btn_pay_crypto", "amount": None, "currency": "USD"}]
    named = plan_button("en", {**PLAN, "key": "90", "days": 90, "stars": 250, "title": "Quarter", "page": page})
    assert named.text == "Quarter · 250 ⭐ / $1.99" and named.callback_data == "plan:90"  # next step: how to pay
    text, markup = payment_choice("en", {**PLAN, "key": "90", "days": 90, "stars": 250}, {"url": "https://pay.x/pay/T", "methods": page})
    rows = [r[0] for r in markup.inline_keyboard]
    assert rows[0].callback_data == "buy:90:250" and rows[1].url == "https://pay.x/pay/T?m=card" and rows[1].text == "💳 Bank card · $1.99"
    assert rows[2].text == "🪙 Crypto" and "90 days" in text  # not connected yet: still a button, the page says "coming soon"


def test_menu_shows_premium_only_when_on_sale():
    labels = lambda money: [b.text for row in menu_keyboard("media", "en", money).keyboard for b in row]
    assert "⭐ Premium" in labels(MONEY)
    assert "⭐ Premium" not in labels({**MONEY, "plans": [], "referrals": None}) and "⭐ Premium" not in labels(None)


def test_card_marks_premium_formats():
    info = {"platform": "archive", "title": "T", "formats": [{"kind": "video", "height": 360, "ext": "mp4", "label": "360p"},
                                                              {"kind": "video", "height": 2160, "ext": "mp4", "label": "4K"}]}
    text, buttons = card(info, "job", "en", "bot", locked={1})
    assert buttons[0][0]["text"].startswith("🎞") and buttons[0][1]["text"].startswith("⭐ 🎞 2160p")
    assert "Premium formats" in text
    assert "Premium" not in card(info, "job", "en", "bot")[0]


def test_join_buttons_are_numbered_for_several_channels():
    from bots.common.runner import channel_keyboard
    one = channel_keyboard("en", [{"chat": "@a", "url": "https://t.me/a"}]).inline_keyboard
    three = channel_keyboard("en", [{"chat": f"@c{i}", "url": f"https://t.me/c{i}"} for i in range(3)]).inline_keyboard
    assert len(one) == 2 and len(three) == 4 and three[2][0].text.endswith(" 3") and three[2][0].url == "https://t.me/c2"
    assert three[-1][0].callback_data == "jn"
