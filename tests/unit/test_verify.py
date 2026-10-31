from pathlib import Path
from unittest.mock import MagicMock
from yt_dlp.utils import DownloadError
from workers.verify import Sample, check, status_for, summary


def ok(platform="archive"):
    return Sample(platform, "video", "https://archive.org/details/x", ok=True, detail="1 file(s)")


def fail(code):
    return Sample("wikimedia", "photo", "https://commons.wikimedia.org/wiki/File:x.jpg", code=code)


def test_status_rules():
    assert status_for([ok(), ok()]) == "VERIFIED"
    assert status_for([ok(), fail("unavailable")]) == "PARTIAL"
    assert status_for([fail("login_required"), fail("no_media")]) == "UNSUPPORTED"
    assert status_for([fail("error:ConnectError")]) == "TEMPORARILY UNAVAILABLE"
    assert summary([ok(), fail("login_required")]).startswith("1/2 samples passed. OK video")


def test_check_downloads_smallest_format(tmp_path):
    adapter = MagicMock()
    adapter.extract.return_value = {"formats": [{"selector": "big", "label": "1080p", "size": 9_000_000},
                                                {"selector": "small", "label": "360p", "size": 1_000}]}

    def download(url, selector, root: Path, limit, merge):
        path = root / "a.mp4"
        path.write_bytes(b"x" * 2000)
        return [path]
    adapter.download.side_effect = download
    sample = check(Sample("archive", "video", "https://archive.org/details/x"), adapter)
    assert sample.ok and adapter.download.call_args.args[1] == "small" and "360p" in sample.detail


def test_check_records_error_codes_not_provider_text():
    adapter = MagicMock()
    adapter.extract.side_effect = DownloadError("ERROR: [archive.org] 1: only available for registered users, secret-url")
    sample = check(Sample("archive", "video", "https://archive.org/details/x"), adapter)
    assert not sample.ok and sample.code == "login_required"
    assert check(Sample("archive", "video", "https://vimeo.com/1"), adapter).code == "platform_mismatch"
