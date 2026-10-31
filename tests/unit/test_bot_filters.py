"""Every handler filter of every bot must evaluate without raising.

Regression: `Command(...) | F.text...` raised TypeError for every incoming message,
so the bots silently ignored all messages on the server.
"""
import asyncio
from datetime import datetime
from unittest.mock import MagicMock
import pytest
from aiogram import Router
from aiogram.types import Chat, Message, User
from bots.common.runner import Context, common_router
from bots.file_sharing import setup as files_setup
from bots.media import setup as media_setup
from bots.video import setup as video_setup

TEXTS = ["hello", "/start", "/help", "/language", "/history", "/myfiles", "❓ Help", "🌐 Language", "🕘 My downloads",
         "📁 My files", "❓ مساعدة", "❓ עזרה", "https://archive.org/details/jNQXAC9IVRw"]


def routers(kind, setup):
    ctx = Context(kind=kind, bot=MagicMock(), api=MagicMock())
    feature = Router()
    setup(feature, ctx)
    return [common_router(ctx), feature]


def message(text):
    return Message(message_id=1, date=datetime.now(), chat=Chat(id=1, type="private"),
                   from_user=User(id=1, is_bot=False, first_name="a"), text=text)


async def matches(kind, setup, text):
    found = []
    bot = MagicMock()
    for router in routers(kind, setup):
        for handler in router.message.handlers:
            ok, _ = await handler.check(message(text), bot=bot)
            if ok:
                found.append(handler.callback.__name__)
    return found


@pytest.mark.parametrize("kind,setup", [("video", video_setup), ("media", media_setup), ("files", files_setup)])
def test_filters_never_raise_and_menu_buttons_match(kind, setup):
    for text in TEXTS:
        asyncio.run(matches(kind, setup, text))  # must not raise
    for text in ("❓ Help", "❓ עזרה", "❓ مساعدة", "/help"):
        assert "help_" in asyncio.run(matches(kind, setup, text))
    assert "choose" in asyncio.run(matches(kind, setup, "🌐 Language"))
