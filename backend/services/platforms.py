"""Source registry: which links the media bot accepts. Extraction itself lives in workers/adapters.py.

Only sources whose content may be downloaded are accepted:
- Wikimedia Commons and the Internet Archive publish media under free licences or in the public domain and offer
  downloads themselves (the licence of every item is shown on its page);
- a direct link to a media file (the user confirms in the bot's terms that they have the right to use it).
Social networks and video platforms whose terms forbid downloading are not supported.
"""
import re
from urllib.parse import urlsplit
from backend.services.security import DomainError

# name -> (yt-dlp extractor keys allowed for it, host suffixes); "direct" has no host list.
PLATFORMS = {
    "wikimedia": (("Wikimedia", "Generic"), ("commons.wikimedia.org", "upload.wikimedia.org")),
    "archive": (("ArchiveOrg", "Generic"), ("archive.org",)),
}
ALL_PLATFORMS = [*PLATFORMS, "direct"]
TITLES = {"wikimedia": "Wikimedia Commons", "archive": "Internet Archive", "direct": "Direct file link"}
MEDIA_FILE = re.compile(r"\.(mp4|webm|mov|mkv|mp3|m4a|ogg|opus|wav|flac|jpe?g|png|webp|gif)$", re.I)


def canonical_url(url: str) -> str:
    return url


def platform_for(url: str) -> str | None:
    """The source of a link, or None when the link is not from a supported source."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    for name, (_, hosts) in PLATFORMS.items():
        if any(host == h or host.endswith("." + h) for h in hosts):
            return name
    return "direct" if MEDIA_FILE.search(parts.path) else None


def extractors_for(platform: str) -> list[str]:
    """Yt-dlp extractors that may handle a link of this source (nothing else, so embedded players are not followed)."""
    return list(PLATFORMS[platform][0]) if platform in PLATFORMS else ["Generic"]


def provider_policy(url: str) -> str:
    """The source of a link; DomainError("unsupported") for links outside the supported sources."""
    name = platform_for(url)
    if not name:
        raise DomainError("unsupported")
    return name
