"""Central localization layer shared by the API, bots, workers and public pages.

Each language is one JSON file in ``locales/``. Adding a language = adding a file;
no handler, worker or schema changes are required. Missing keys fall back to English.

Administrators edit any text and switch languages off in the dashboard (Settings → Translations). Those changes are
stored in the database and laid over the files: the API and the workers read them (refreshed every 30 seconds), the
bots receive them with their heartbeat. An edited text keeps the placeholders of the original.
"""
import html
import json
import time
from functools import lru_cache
from pathlib import Path

LOCALES_DIR = Path(__file__).with_name("locales")
FALLBACK = "en"
RLM = "‏"
REFRESH_SECONDS = 30

_edits: dict = {"texts": {}, "disabled": []}  # {"texts": {lang: {key: text}}, "disabled": [codes]}
_loader = None
_loaded = 0.0


@lru_cache
def catalogs() -> dict[str, dict]:
    return {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in sorted(LOCALES_DIR.glob("*.json"))}


def use_loader(loader) -> None:
    """The API and the workers read the dashboard's edits from the database with this function."""
    global _loader, _loaded
    _loader, _loaded = loader, 0.0


def set_edits(value: dict | None) -> None:
    """Bots get the edits from the API (heartbeat) and set them here."""
    global _edits
    value = value or {}
    _edits = {"texts": {str(lang): {str(k): str(v) for k, v in (texts or {}).items()} for lang, texts in (value.get("texts") or {}).items()},
              "disabled": [str(code) for code in value.get("disabled") or [] if code != FALLBACK]}


def edits() -> dict:
    global _loaded
    if _loader and time.monotonic() - _loaded > REFRESH_SECONDS:
        _loaded = time.monotonic()
        try:
            set_edits(_loader())
        except Exception:
            pass  # the files still work: never break a message because the database is busy
    return _edits


def all_languages() -> dict[str, str]:
    """Every language with a file, switched off or not (the dashboard's list)."""
    rank = lambda code: (code != FALLBACK, catalogs()[code]["_meta"].get("order", 99), code)
    label = lambda meta: f"{meta['flag']} {meta['name']}" if meta.get("flag") else meta["name"]
    return {code: label(catalogs()[code]["_meta"]) for code in sorted(catalogs(), key=rank)}


def enabled(code: str) -> bool:
    return code in catalogs() and (code == FALLBACK or code not in edits()["disabled"])


def languages() -> dict[str, str]:
    """Language code -> flag and native name ("🇪🇸 Español"): the fallback first, then `_meta.order` (most spoken first).
    Languages switched off in the dashboard are not offered."""
    return {code: name for code, name in all_languages().items() if enabled(code)}


def is_rtl(lang: str) -> bool:
    return bool(catalogs().get(lang, {}).get("_meta", {}).get("rtl"))


def resolve(code: str | None, default: str = FALLBACK) -> str:
    """Map a Telegram language_code such as 'ar-SA' or 'pt-br' to a supported language."""
    if code:
        base = code.lower().replace("_", "-").split("-")[0]
        base = {"iw": "he", "in": "hi"}.get(base, base)  # legacy codes still sent by some clients; zh-hans/zh-tw -> zh
        if enabled(base):
            return base
    return default if enabled(default) else FALLBACK


def raw(lang: str, key: str) -> str:
    texts = edits()["texts"]
    return (texts.get(lang, {}).get(key) or catalogs().get(lang, {}).get(key) or texts.get(FALLBACK, {}).get(key)
            or catalogs()[FALLBACK].get(key) or catalogs()[FALLBACK]["failed"])


def placeholders(text: str) -> set[str]:
    import string
    return {field for _, field, _, _ in string.Formatter().parse(text) if field}


def tr(lang: str, key: str, **kwargs) -> str:
    """Translated HTML-safe text. Interpolated values are escaped; RTL texts get an RLM mark."""
    values = {k: html.escape(str(v), quote=False) for k, v in kwargs.items()}
    try:
        text = raw(lang, key).format(**values)
    except (KeyError, IndexError, ValueError):  # a broken edit never breaks the bot: the original text
        text = (catalogs().get(lang, {}).get(key) or catalogs()[FALLBACK].get(key, key)).format(**values)
    return (RLM + text) if is_rtl(lang) else text
