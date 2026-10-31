"""Videos are delivered as playable videos (with size, length and cover), albums of photos and videos as one album."""
import shutil
import subprocess
import pytest
from workers import telegram


class Recorder(telegram.Telegram):
    def __init__(self):
        self.calls = []

    def call(self, method, data, files=None):
        self.calls.append((method, data, sorted(files or {})))
        return {}


def test_mixed_album_is_sent_as_photos_and_videos_not_files(tmp_path, monkeypatch):
    monkeypatch.setattr(telegram, "video_meta", lambda p: ({"width": 720, "height": 1280, "duration": 119}, None))
    photo, video, other = tmp_path / "a.jpg", tmp_path / "b.mp4", tmp_path / "c.pdf"
    for p in (photo, video, other):
        p.write_bytes(b"x")
    bot = Recorder()
    bot.media_group(1, [photo, video], "- @bot - 1 / 2")
    method, data, _ = bot.calls[0]
    assert method == "sendMediaGroup" and [m["type"] for m in data["media"]] == ["photo", "video"]
    assert data["media"][1]["width"] == 720 and data["media"][1]["supports_streaming"] and data["media"][0]["caption"] == "- @bot - 1 / 2"
    bot.media_group(1, [photo, other], "")
    assert {m["type"] for m in bot.calls[1][1]["media"]} == {"document"}  # Telegram cannot mix documents with photos


def test_single_video_has_player_details(tmp_path, monkeypatch):
    thumb = tmp_path / "t.jpg"
    thumb.write_bytes(b"j")
    monkeypatch.setattr(telegram, "video_meta", lambda p: ({"width": 720, "height": 1280, "duration": 119}, thumb))
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    bot = Recorder()
    bot.media(1, video, "cap")
    method, data, files = bot.calls[0]
    assert method == "sendVideo" and data["height"] == "1280" and data["thumbnail"] == "attach://thumbnail" and "thumbnail" in files


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg not installed")
def test_video_meta_reads_a_real_file(tmp_path):
    video = tmp_path / "v.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=red:s=360x640:d=3", "-pix_fmt", "yuv420p", str(video)], check=True)
    meta, thumb = telegram.video_meta(video)
    assert meta == {"width": 360, "height": 640, "duration": 3} and thumb and thumb.exists()


def test_the_mp4_copy_stays_a_file_not_a_second_video(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    bot = Recorder()
    bot.document(1, video)
    method, data, files = bot.calls[0]
    assert method == "sendDocument" and data["disable_content_type_detection"] == "true" and files == ["document"]
