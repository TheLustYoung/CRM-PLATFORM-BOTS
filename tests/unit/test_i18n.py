import string
from backend.services import i18n


def test_every_language_has_every_key():
    base = set(i18n.catalogs()["en"])
    for lang, catalog in i18n.catalogs().items():
        assert set(catalog) == base, lang


def test_templates_format_and_escape():
    for lang, catalog in i18n.catalogs().items():
        for key, value in catalog.items():
            if key == "_meta":
                continue
            fields = {field: "<x>" for _, field, _, _ in string.Formatter().parse(value) if field}
            text = i18n.tr(lang, key, **fields)
            assert "<x>" not in text, (lang, key)


def test_fallback_rtl_and_detection():
    assert i18n.tr("unknown", "revoked") == i18n.tr("en", "revoked")
    assert i18n.tr("ar", "revoked").startswith(i18n.RLM) and i18n.is_rtl("ar") and not i18n.is_rtl("en")
    assert i18n.is_rtl("he") and i18n.resolve("he-IL") == "he" and i18n.resolve("iw") == "he"
    assert set(i18n.catalogs()["he"]) == set(i18n.catalogs()["en"])  # every key translated
    assert i18n.resolve("ar-SA") == "ar" and i18n.resolve("de", "en") == "en" and i18n.resolve(None) == "en"
    assert list(i18n.languages())[0] == "en"


def test_world_languages_in_order():
    """Top-10 spoken languages and every UN official language (each once), plus Hebrew."""
    assert list(i18n.languages()) == ["en", "zh", "hi", "es", "ar", "fr", "bn", "pt", "ru", "ur", "he"]
    assert i18n.resolve("RU") == "ru" and i18n.resolve("zh-hans") == "zh" and i18n.resolve("pt-br") == "pt" and i18n.resolve("in") == "hi"
    assert i18n.is_rtl("ur") and i18n.tr("ur", "revoked").startswith(i18n.RLM) and not i18n.is_rtl("zh")
    for lang in i18n.catalogs():  # HTML tags stay balanced in every translation (Telegram rejects broken markup)
        for key, value in i18n.catalogs()[lang].items():
            if key != "_meta":
                assert value.count("<b>") == value.count("</b>"), (lang, key)
