from yt_dlp.utils import DownloadError
from workers.tasks import download_error_code


def test_download_errors_map_to_honest_codes():
    assert download_error_code(DownloadError("ERROR: [archive.org] 1: This item is only available for registered users.")) == "login_required"
    assert download_error_code(DownloadError("ERROR: [Wikimedia] 1: No video formats found!")) == "no_media"
    assert download_error_code(DownloadError("ERROR: Unsupported URL: https://x")) == "unsupported"
    assert download_error_code(DownloadError("ERROR: HTTP Error 404")) == "unavailable"
    assert download_error_code(DownloadError("ERROR: [archive.org] x: This item is restricted.")) == "login_required"
