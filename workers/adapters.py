"""Yt-dlp based media adapter for the supported sources (backend/services/platforms.py).

Only formats that the extractor reports for the specific URL are offered: nothing is invented, no conversions are
advertised. Each source is limited to its own extractors (yt-dlp `allowed_extractors`), so a page that embeds a
player from another site is not followed. No logins, cookies, proxies or DRM handling of any kind.
"""
import logging
import re
from pathlib import Path
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
from backend.config import settings
from backend.services.platforms import extractors_for, platform_for, provider_policy
from backend.services.security import normalize_url, DomainError

log = logging.getLogger(__name__)
VIDEO_EXT = {"mp4", "webm", "mov", "mkv"}
AUDIO_EXT = {"m4a", "mp3", "webm", "opus", "ogg", "aac", "flac", "wav"}
IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_VIDEO_OPTIONS, MAX_AUDIO_OPTIONS, MAX_ITEMS = 8, 4, 20


class QuietLogger:
    def debug(self, *_): pass
    def warning(self, *_): pass
    def error(self, *_): pass


def has(value) -> bool:
    return value not in (None, "none")


def size_of(f: dict, duration: float | None = None) -> int | None:
    """Reported size, else an estimate from bitrate × duration (shown with ≈), else unknown."""
    size = f.get("filesize") or f.get("filesize_approx")
    if not size and duration and f.get("tbr"):
        size = int(f["tbr"] * 1000 / 8 * duration)
    return size or None


def safe_id(f: dict) -> str | None:
    fid = str(f.get("format_id") or "")
    return fid if re.fullmatch(r"[\w.-]{1,64}", fid) else None


def build_formats(raw: list[dict], duration: float | None = None) -> list[dict]:
    """Group the extractor's formats into a short, honest menu of video and audio options."""
    def size(f: dict) -> int | None:
        return size_of(f, duration)

    usable = [f for f in raw if f.get("url") and not f.get("has_drm") and safe_id(f) and f.get("ext") in VIDEO_EXT | AUDIO_EXT | IMAGE_EXT]
    images = [f for f in usable if f["ext"] in IMAGE_EXT and not has(f.get("vcodec"))]
    audio = [f for f in usable if f["ext"] in AUDIO_EXT and f.get("vcodec") == "none" and has(f.get("acodec"))]
    video = [f for f in usable if f["ext"] in VIDEO_EXT and f not in audio and f not in images
             and (has(f.get("vcodec")) or (f.get("vcodec") is None and f.get("acodec") is None))]

    def best_audio(ext: str) -> dict | None:
        preferred = [a for a in audio if a["ext"] == ("m4a" if ext == "mp4" else "webm")] or audio
        return max(preferred, key=lambda a: a.get("abr") or a.get("tbr") or 0, default=None)

    result = []
    by_quality: dict[tuple, dict] = {}
    # Same height and container: H.264 first (plays in every Telegram app), then bitrate.
    rank = lambda f: (str(f.get("vcodec") or "").startswith(("avc", "h264")), f.get("tbr") or 0)
    for f in video:
        key = (f.get("height"), f["ext"])
        if key not in by_quality or rank(f) > rank(by_quality[key]):
            by_quality[key] = f
    for (height, ext), f in sorted(by_quality.items(), key=lambda item: (item[0][0] or 0, item[0][1] == "mp4"), reverse=True)[:MAX_VIDEO_OPTIONS]:
        fid, silent = safe_id(f), f.get("acodec") == "none"
        partner = best_audio(ext) if silent else None
        total = size(f)
        if partner:
            # Video-only stream + matching audio track, merged by FFmpeg into the same container.
            selector = f"{fid}+{safe_id(partner)}"
            total = total + size(partner) if total and size(partner) else None
        else:
            selector = fid
        label = f"{ext.upper()} · {height}p" if height else ext.upper()
        if silent and not partner:
            label += " · no audio"
        result.append({"selector": selector, "kind": "video", "ext": ext, "height": height, "size": total,
                       "merge": ext if partner and ext in {"mp4", "webm"} else ("mkv" if partner else None), "label": label})
    by_bitrate: dict[tuple, dict] = {}
    for f in audio:
        key = (f["ext"], round((f.get("abr") or 0) / 16))
        if key not in by_bitrate or (f.get("abr") or 0) > (by_bitrate[key].get("abr") or 0):
            by_bitrate[key] = f
    for f in sorted(by_bitrate.values(), key=lambda a: a.get("abr") or 0, reverse=True)[:MAX_AUDIO_OPTIONS]:
        abr = round(f["abr"]) if f.get("abr") else None
        label = f"{f['ext'].upper()} · {abr} kbps" if abr else f"{f['ext'].upper()}"
        result.append({"selector": safe_id(f), "kind": "audio", "ext": f["ext"], "abr": abr, "size": size(f), "merge": None, "label": label})
    for f in images[:1]:
        result.append({"selector": safe_id(f), "kind": "image", "ext": f["ext"], "size": size(f), "merge": None, "label": f"Image · {f['ext'].upper()}"})
    return result


def downloaded(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if p.is_file() and p.suffix not in {".part", ".ytdl", ".temp"})


def fitting_format(max_bytes: int) -> str:
    """Best quality whose reported or estimated size fits the limit; the smallest one as the last resort."""
    limit = max(max_bytes // 1_000_000 - 1, 1)
    fits = f"[filesize<{limit}M]"
    approx = f"[filesize_approx<{limit}M]"
    return f"bv*{fits}+ba{fits}/b{fits}/bv*{approx}+ba{approx}/b{approx}/wv*+wa/w"


def too_large(info: dict | None, max_bytes: int) -> bool:
    """Whether the chosen format(s) exceed the limit, from reported or bitrate-estimated sizes."""
    if not info:
        return False
    chosen = info.get("requested_formats") or [info]
    sizes = [size_of(f, info.get("duration")) for f in chosen]
    return all(sizes) and sum(sizes) > max_bytes


def checked_url(url: str) -> str:
    """Validate a user URL. Behind the egress proxy the worker has no DNS of its own (private Docker
    network), so the public-address check is left to the proxy, which resolves and pins every host."""
    return normalize_url(url, resolve=not settings().egress_proxy)


class MediaAdapter:
    def client(self, options: dict) -> YoutubeDL:
        return YoutubeDL(options)

    def options(self, platform: str, root: Path | None = None, max_bytes: int = 200_000_000, on_progress=None,
                should_stop=None) -> dict:
        def size_guard(progress):
            if (progress.get("downloaded_bytes") or 0) > max_bytes:
                raise DomainError("file_size")
            if should_stop and should_stop():
                raise DomainError("cancelled")  # Cancel button: stops yt-dlp between chunks
            if on_progress and progress.get("status") == "downloading":
                try:
                    on_progress(progress.get("downloaded_bytes") or 0, progress.get("total_bytes") or progress.get("total_bytes_estimate"))
                except Exception:
                    pass  # progress display must never break a download
        options = {
            "quiet": True, "no_warnings": True, "logger": QuietLogger(), "noplaylist": True, "playlistend": MAX_ITEMS,
            "socket_timeout": 25, "retries": 2, "fragment_retries": 2, "max_filesize": max_bytes,
            "progress_hooks": [size_guard], "enable_file_urls": False, "restrictfilenames": True, "cachedir": False,
            "allowed_extractors": extractors_for(platform),
            "outtmpl": str(root / "%(autonumber)03d-%(title).80B.%(ext)s") if root else "%(id)s.%(ext)s",
        }
        if settings().egress_proxy:
            options["proxy"] = settings().egress_proxy  # SSRF guard: the egress proxy refuses private addresses
        return options

    def run_ytdlp(self, options: dict, url: str, download: bool):
        with self.client(options) as ydl:
            return ydl.extract_info(url, download=download)

    def extract(self, url: str) -> dict:
        url = checked_url(url)
        platform = provider_policy(url)
        info = self.run_ytdlp(self.options(platform), url, download=False)
        if not info:
            raise DomainError("unavailable")
        entries = [e for e in info.get("entries") or [] if e] if info.get("_type") == "playlist" or "entries" in info else [info]
        if not entries:
            raise DomainError("unavailable")
        if len(entries) > MAX_ITEMS:
            raise DomainError("unsupported")
        first = entries[0]
        if len(entries) > 1:
            formats = [{"selector": "best", "kind": "collection", "count": len(entries), "size": None, "merge": None, "label": f"{len(entries)}"}]
        else:
            raw = first.get("formats") or ([first] if first.get("url") else [])
            formats = build_formats(raw, first.get("duration"))
        if not formats:
            raise DomainError("unsupported")
        source = info if len(entries) > 1 else first
        text = lambda value, limit: str(value)[:limit] if value not in (None, "") else None
        return {
            "platform": platform, "extractor": str(first.get("extractor_key") or "")[:40],
            "title": text(source.get("title") or first.get("title"), 250) or "Media",
            "channel": text(source.get("channel") or source.get("uploader") or first.get("uploader"), 100),
            "duration": first.get("duration") if len(entries) == 1 else None,
            "date": text(source.get("upload_date") or first.get("upload_date"), 8),
            "views": source.get("view_count"), "likes": source.get("like_count"), "comments": source.get("comment_count"),
            "description": text(source.get("description") or first.get("description"), 3500),
            "license": text(source.get("license") or first.get("license"), 200),
            "thumbnail": source.get("thumbnail") or first.get("thumbnail"),
            "webpage_url": text(source.get("webpage_url") or url, 500), "count": len(entries), "formats": formats,
        }

    def download(self, url: str, selector: str, root: Path, max_bytes: int, merge: str | None = None, on_progress=None,
                 should_stop=None) -> list[Path]:
        url = checked_url(url)
        platform = provider_policy(url)
        options = self.options(platform, root, max_bytes, on_progress, should_stop)
        options["format"] = selector
        if merge:
            options["merge_output_format"] = merge
        info = self.run_ytdlp(options, url, download=True)
        if not downloaded(root) and too_large(info, max_bytes):
            # The chosen quality does not fit the limit: take the best one that does, so content still arrives.
            options["format"] = fitting_format(max_bytes)
            options.pop("merge_output_format", None)
            info = self.run_ytdlp(options, url, download=True)
        files = downloaded(root)
        if not files:
            # yt-dlp silently skips a format above max_filesize: say "too large", not "unavailable".
            raise DomainError("file_size" if too_large(info, max_bytes) else "unavailable")
        if sum(f.stat().st_size for f in files) > max_bytes or len(files) > MAX_ITEMS:
            raise DomainError("file_size")
        if len(files) == 1:
            # The numeric prefix only keeps album order; a single file gets its clean title.
            clean = files[0].with_name(re.sub(r"^\d{3}-", "", files[0].name) or files[0].name)
            files = [files[0].rename(clean)] if clean != files[0] else files
        return files


__all__ = ["MediaAdapter", "DownloadError", "build_formats", "platform_for"]
