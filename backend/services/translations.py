"""Translations edited in the dashboard: any bot text in any language, and which languages are on.

Stored as one system setting {"texts": {lang: {key: text}}, "disabled": [codes]} and laid over the locale files by
backend.services.i18n. An edited text must keep the placeholders of the original ({name}, {count}, ...) and use only
Telegram's HTML tags, so a typo can never break a bot message. An empty text brings back the original.
"""
from html.parser import HTMLParser
from backend.models import SystemSetting
from backend.services import i18n

KEY = "translations"
MAX_LENGTH = 4000
TAGS = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "a", "code", "pre", "tg-spoiler", "blockquote"}


class TranslationError(ValueError):
    def __init__(self, code: str, key: str = ""):
        super().__init__(code)
        self.code, self.key = code, key


def load(db) -> dict:
    row = db.get(SystemSetting, KEY)
    value = row.value if row else {}
    return {"texts": value.get("texts") or {}, "disabled": value.get("disabled") or []}


def loader():
    """For i18n.use_loader in the API and the workers."""
    from backend.database import Session
    with Session() as db:
        return load(db)


class _Tags(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.bad = [], False

    def handle_starttag(self, tag, attrs):
        if tag not in TAGS:
            self.bad = True
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            self.bad = True


def check(key: str, text: str) -> str:
    original = i18n.catalogs()[i18n.FALLBACK].get(key)
    if key.startswith("_") or not isinstance(original, str):
        raise TranslationError("unknown_key", key)
    text = (text or "").strip()
    if len(text) > MAX_LENGTH:
        raise TranslationError("text_too_long", key)
    try:
        used = i18n.placeholders(text)
    except ValueError:
        raise TranslationError("bad_placeholder", key) from None
    if not used <= i18n.placeholders(original):
        raise TranslationError("bad_placeholder", key)
    parser = _Tags()
    parser.feed(text)
    parser.close()
    if parser.bad or parser.stack:
        raise TranslationError("bad_html", key)
    return text


def texts(db, lang: str) -> list[dict]:
    """Every text of a language: the file's version, the English original and the dashboard's edit (if any)."""
    if lang not in i18n.catalogs():
        raise TranslationError("unknown_language")
    edited = load(db)["texts"].get(lang, {})
    english, own = i18n.catalogs()[i18n.FALLBACK], i18n.catalogs()[lang]
    return [{"key": key, "english": value, "default": own.get(key) or "", "value": edited.get(key, ""),
             "placeholders": sorted(i18n.placeholders(value))}
            for key, value in english.items() if not key.startswith("_") and isinstance(value, str)]


def save(db, lang: str, values: dict[str, str]) -> int:
    """Saves the edits of one language (all or nothing); returns how many texts differ from the files now."""
    if lang not in i18n.catalogs():
        raise TranslationError("unknown_language")
    data = load(db)
    current = dict(data["texts"].get(lang, {}))
    for key, value in values.items():
        text = check(key, value)
        default = i18n.catalogs()[lang].get(key) or ""
        if not text or text == default.strip():
            current.pop(key, None)
        else:
            current[key] = text
    data["texts"] = {**data["texts"], lang: current}
    db.merge(SystemSetting(key=KEY, value=data))
    db.commit()
    i18n.set_edits(data)
    return len(current)


def set_enabled(db, lang: str, on: bool) -> list[str]:
    if lang not in i18n.catalogs():
        raise TranslationError("unknown_language")
    if lang == i18n.FALLBACK and not on:
        raise TranslationError("fallback_language")  # the language every missing text falls back to stays on
    data = load(db)
    disabled = [code for code in data["disabled"] if code != lang] + ([] if on else [lang])
    data["disabled"] = sorted(set(disabled))
    db.merge(SystemSetting(key=KEY, value=data))
    db.commit()
    i18n.set_edits(data)
    return data["disabled"]


def counts(db) -> dict[str, int]:
    return {lang: len(values) for lang, values in load(db)["texts"].items()}
