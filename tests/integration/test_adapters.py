import os
import pytest
from unittest.mock import patch
from backend.services.platforms import extractors_for, platform_for, provider_policy
from backend.services.security import DomainError
from workers.adapters import MediaAdapter

CASES = [
    ("archive", "https://archive.org/details/example-film"),
    ("wikimedia", "https://commons.wikimedia.org/wiki/File:Example.webm"),
    ("direct", "https://cdn.example.org/clips/sample.mp4"),
]


@pytest.mark.parametrize("platform,url", CASES)
def test_source_adapter_contract(platform, url):
    # Mocked extractor contract, explicitly NOT a live provider verification.
    assert platform_for(url) == platform
    info = {"title": "fixture", "like_count": 3, "license": "CC BY-SA 4.0",
            "formats": [{"format_id": "18", "url": "https://cdn.example/v", "height": 360, "ext": "mp4", "vcodec": "h264", "acodec": "aac", "filesize": 1000}]}
    with patch("workers.adapters.normalize_url", return_value=url), patch("workers.adapters.YoutubeDL") as mock:
        mock.return_value.__enter__.return_value.extract_info.return_value = info
        result = MediaAdapter().extract(url)
        options = mock.call_args.args[0]
    assert result["platform"] == platform and result["likes"] == 3 and result["comments"] is None
    assert result["license"] == "CC BY-SA 4.0"
    assert result["formats"][0]["selector"] == "18" and result["formats"][0]["label"] == "MP4 · 360p"
    assert options["allowed_extractors"] == extractors_for(platform)  # embedded players of other sites are not followed
    assert "cookiefile" not in options and "extractor_args" not in options


def test_collection_becomes_album():
    url = "https://commons.wikimedia.org/wiki/File:abc.jpg"
    info = {"_type": "playlist", "title": "Post", "entries": [{"url": "https://cdn/1.jpg", "ext": "jpg"}, {"url": "https://cdn/2.jpg", "ext": "jpg"}]}
    with patch("workers.adapters.normalize_url", return_value=url), patch("workers.adapters.YoutubeDL") as mock:
        mock.return_value.__enter__.return_value.extract_info.return_value = info
        result = MediaAdapter().extract(url)
    assert result["count"] == 2 and result["formats"][0]["kind"] == "collection"


def test_spoofed_hosts_are_not_trusted():
    assert platform_for("https://archive.org.attacker.example/details/x") is None
    assert platform_for("https://commons.wikimedia.org.evil.example/wiki/File:x.jpg") == "direct"  # only as a plain file link


@pytest.mark.parametrize("url", ["https://www.youtube.com/watch?v=x", "https://www.instagram.com/p/abc/", "https://www.tiktok.com/@a/video/1",
                                 "https://x.com/a/status/1", "https://vimeo.com/123", "https://example.com/page.html"])
def test_platforms_that_forbid_downloading_are_rejected(url):
    with pytest.raises(DomainError, match="unsupported"):
        provider_policy(url)


@pytest.mark.live
@pytest.mark.parametrize("platform,url", CASES)
def test_live_sources(platform, url, tmp_path):
    actual = os.getenv(f"LIVE_{platform.upper()}_URL")
    if not actual or os.getenv("RUN_LIVE_TESTS") != "1":
        pytest.skip("NOT VERIFIED: set RUN_LIVE_TESTS=1 and LIVE_<SOURCE>_URL")
    result = MediaAdapter().extract(actual)
    assert result["title"] and result["formats"]
    smallest = min(result["formats"], key=lambda f: f.get("size") or 10**12)
    paths = MediaAdapter().download(actual, smallest["selector"], tmp_path, 50_000_000, smallest.get("merge"))
    assert paths and all(p.stat().st_size > 0 for p in paths)
