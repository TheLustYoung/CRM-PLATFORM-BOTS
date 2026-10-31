"""Minimal synchronous Telegram Bot API client used by workers to deliver results."""
import json
import shutil
import subprocess
from contextlib import ExitStack
from pathlib import Path
import httpx
from backend.config import settings
from backend.services.security import DomainError, normalize_url

PHOTO_LIMIT = 10_000_000
VIDEO_EXT, AUDIO_EXT, PHOTO_EXT = {".mp4", ".mov"}, {".mp3", ".m4a"}, {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_FIELDS = {"width", "height", "duration", "thumbnail", "supports_streaming"}


def kind_of(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXT:
        return "video"
    if suffix in AUDIO_EXT:
        return "audio"
    if suffix in PHOTO_EXT and path.stat().st_size <= PHOTO_LIMIT:
        return "photo"
    return "document"


def video_meta(path: Path) -> tuple[dict, Path | None]:
    """Size, length and a cover frame, so Telegram shows a proper player instead of a square or black preview."""
    meta, thumb = {}, None
    probe, ffmpeg = shutil.which("ffprobe"), shutil.which("ffmpeg")
    try:
        if probe:
            out = subprocess.run([probe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                                  "-of", "json", str(path)], capture_output=True, timeout=20, check=True).stdout
            info = json.loads(out or b"{}")
            stream = (info.get("streams") or [{}])[0]
            meta = {k: int(stream[k]) for k in ("width", "height") if stream.get(k)}
            if (info.get("format") or {}).get("duration"):
                meta["duration"] = round(float(info["format"]["duration"]))
        if ffmpeg:
            target = path.with_name(path.stem + ".thumb.jpg")
            seek = "1" if meta.get("duration", 2) >= 2 else "0"
            subprocess.run([ffmpeg, "-y", "-v", "error", "-ss", seek, "-i", str(path), "-frames:v", "1",
                            "-vf", "scale=320:320:force_original_aspect_ratio=decrease", "-q:v", "5", str(target)],
                           capture_output=True, timeout=30, check=True)
            if target.exists() and 0 < target.stat().st_size <= 200_000:
                thumb = target
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return meta, thumb


class TelegramError(DomainError):
    """Telegram rejected the request; `description` is Telegram's own text (never contains the token)."""

    def __init__(self, description: str):
        super().__init__("failed")
        self.description = description


class TelegramRetry(httpx.TransportError):
    """Temporary failure or flood control; `retry_after` seconds when Telegram says so."""

    def __init__(self, retry_after: int | None = None):
        super().__init__("Telegram temporarily unavailable")
        self.retry_after = retry_after


class Telegram:
    def __init__(self, kind: str):
        self.base = f"https://api.telegram.org/bot{settings().bot_token(kind)}/"
        self.client = httpx.Client(proxy=settings().egress_proxy or None, timeout=120, follow_redirects=False)

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def call(self, method: str, data: dict, files=None):
        # Never log the URL: Telegram embeds the bot token in it.
        body = {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in data.items() if v is not None}
        response = self.client.post(self.base + method, data=body, files=files)
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        if response.status_code >= 500 or response.status_code == 429:
            raise TelegramRetry((payload.get("parameters") or {}).get("retry_after"))
        if response.status_code != 200 or not payload.get("ok"):
            raise TelegramError(str(payload.get("description") or f"HTTP {response.status_code}")[:300])
        return payload["result"]

    def file_bytes(self, file_id: str, max_size: int = 10_000_000) -> bytes:
        info = self.call("getFile", {"file_id": file_id})
        remote_path = info.get("file_path") or ""
        if not remote_path or ".." in remote_path or remote_path.startswith("/") or (info.get("file_size") or 0) > max_size:
            raise DomainError("failed")
        response = self.client.get(self.base.replace("/bot", "/file/bot", 1) + remote_path)
        if response.status_code != 200 or len(response.content) > max_size:
            raise DomainError("unavailable")
        return response.content

    @staticmethod
    def markup(buttons):
        return {"inline_keyboard": buttons} if buttons else None

    def message(self, chat_id, text, buttons=None):
        return self.call("sendMessage", {"chat_id": chat_id, "text": text[:4096], "parse_mode": "HTML",
                                         "link_preview_options": {"is_disabled": True}, "reply_markup": self.markup(buttons)})

    def edit(self, chat_id, message_id, text, buttons=None):
        # Without reply_markup Telegram removes the inline keyboard, so the buttons are sent with every edit.
        return self.call("editMessageText", {"chat_id": chat_id, "message_id": message_id, "text": text[:4096], "parse_mode": "HTML",
                                             "reply_markup": self.markup(buttons)})

    def delete(self, chat_id, message_id):
        return self.call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    def photo_url(self, chat_id, url, caption=None, buttons=None):
        return self.call("sendPhoto", {"chat_id": chat_id, "photo": normalize_url(url, resolve=False), "caption": caption,
                                       "parse_mode": "HTML" if caption else None, "reply_markup": self.markup(buttons)})

    def media(self, chat_id, path: Path, caption: str, buttons=None):
        """Send a file with the most suitable Telegram type; fall back to a document."""
        field = kind_of(path)
        method = {"video": "sendVideo", "audio": "sendAudio", "photo": "sendPhoto"}.get(field, "sendDocument")
        data = {"chat_id": chat_id, "caption": caption[:1024], "parse_mode": "HTML", "reply_markup": self.markup(buttons)}
        try:
            with ExitStack() as stack:
                files = {field: (path.name, stack.enter_context(path.open("rb")), "application/octet-stream")}
                if field == "video":
                    meta, thumb = video_meta(path)
                    data.update({k: str(v) for k, v in meta.items()}, supports_streaming="true")
                    if thumb:
                        files["thumbnail"] = ("thumb.jpg", stack.enter_context(thumb.open("rb")), "image/jpeg")
                        data["thumbnail"] = "attach://thumbnail"
                return self.call(method, data, files=files)
        except DomainError:
            if method == "sendDocument":
                raise
            with path.open("rb") as body:
                return self.call("sendDocument", {k: v for k, v in data.items() if k not in VIDEO_FIELDS},
                                 files={"document": (path.name, body, "application/octet-stream")})

    def document(self, chat_id, path: Path, caption: str = ""):
        """The original file to save, next to the playable video or photo. Telegram would turn an .mp4 sent as a document
        into a second video; disable_content_type_detection keeps it a file (name, size, download arrow)."""
        with path.open("rb") as body:
            return self.call("sendDocument", {"chat_id": chat_id, "caption": caption[:1024] or None, "parse_mode": "HTML" if caption else None,
                                              "disable_content_type_detection": "true"},
                             files={"document": (path.name, body, "application/octet-stream")})

    def media_group(self, chat_id, paths: list[Path], caption: str):
        """Album in original order; the caption is attached once, to the first item.
        Photos and videos are shown as a playable album; anything else goes as documents (Telegram cannot mix them)."""
        for start in range(0, len(paths), 10):
            chunk = paths[start:start + 10]
            if len(chunk) == 1:
                self.media(chat_id, chunk[0], caption if start == 0 else "")
                continue
            kinds = [kind_of(p) for p in chunk]
            visual = all(k in ("photo", "video") for k in kinds)
            with ExitStack() as stack:
                items, files = [], {}
                for i, (p, k) in enumerate(zip(chunk, kinds)):
                    item = {"type": k if visual else "document", "media": f"attach://f{i}"}
                    files[f"f{i}"] = (p.name, stack.enter_context(p.open("rb")), "application/octet-stream")
                    if visual and k == "video":
                        meta, thumb = video_meta(p)
                        item.update(meta, supports_streaming=True)
                        if thumb:
                            files[f"t{i}"] = ("thumb.jpg", stack.enter_context(thumb.open("rb")), "image/jpeg")
                            item["thumbnail"] = f"attach://t{i}"
                    if start == 0 and i == 0:
                        item.update(caption=caption[:1024], parse_mode="HTML")
                    items.append(item)
                self.call("sendMediaGroup", {"chat_id": chat_id, "media": items}, files=files)

    def download_file(self, file_id: str, destination: Path, max_size: int, should_stop=None):
        info = self.call("getFile", {"file_id": file_id})
        if (info.get("file_size") or 0) > max_size:
            raise DomainError("file_size")
        remote_path = info["file_path"]
        if ".." in remote_path or remote_path.startswith("/"):
            raise DomainError("failed")
        url = self.base.replace("/bot", "/file/bot", 1) + remote_path
        size = 0
        with self.client.stream("GET", url) as response:
            if response.status_code != 200:
                raise DomainError("unavailable")
            with destination.open("wb") as output:
                for chunk in response.iter_bytes(256 * 1024):
                    size += len(chunk)
                    if size > max_size:
                        raise DomainError("file_size")
                    if should_stop and should_stop():
                        raise DomainError("cancelled")
                    output.write(chunk)

    def get_me(self) -> dict:
        return self.call("getMe", {})
