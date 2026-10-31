"""Video Bot: videos from free-licence libraries (Internet Archive, Wikimedia Commons) with quality choice and licence."""
from aiogram import Router
from bots.common.media_flow import setup_media
from bots.common.runner import Context


def setup(router: Router, ctx: Context):
    setup_media(router, ctx, libraries_only=True)
