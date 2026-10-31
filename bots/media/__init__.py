"""Media Bot: openly licensed media (Wikimedia Commons, Internet Archive) and direct links to media files."""
from aiogram import Router
from bots.common.media_flow import setup_media
from bots.common.runner import Context


def setup(router: Router, ctx: Context):
    setup_media(router, ctx, libraries_only=False)
