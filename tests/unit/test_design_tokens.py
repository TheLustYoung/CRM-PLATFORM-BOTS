"""The dashboard's colour tokens keep text readable: WCAG AA contrast (4.5:1) for every text colour on every surface,
in both themes. Tokens are read straight from dashboard/src/styles/abstracts/_tokens.scss."""
import re
from pathlib import Path
import pytest

TOKENS = Path(__file__).resolve().parents[2] / "dashboard" / "src" / "styles" / "abstracts" / "_tokens.scss"
TEXT = ["heading", "text", "muted"]
SURFACES = ["bg", "surface", "surface-2"]


def theme(name: str) -> dict[str, str]:
    source = TOKENS.read_text(encoding="utf-8")
    brand = dict(re.findall(r"([\w-]+): (#[0-9a-fA-F]{6})", re.search(r"\$brand: \((.*?)\);", source, re.S).group(1)))
    block = re.search(rf"\b{name}: \((.*?)\n  \)", source, re.S).group(1)
    colours = dict(re.findall(r"([\w-]+): (#[0-9a-fA-F]{6})", block))
    colours.update({key: brand[ref] for key, ref in re.findall(r"([\w-]+): map\.get\(\$brand, ([\w-]+)\)", block)})
    return colours


def luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("name", ["dark", "light"])
def test_text_tokens_meet_wcag_aa_on_every_surface(name):
    colours = theme(name)
    for text in TEXT:
        for surface in SURFACES:
            ratio = contrast(colours[text], colours[surface])
            assert ratio >= 4.5, f"{name}: {text} on {surface} is {ratio:.2f}:1"


@pytest.mark.parametrize("name", ["dark", "light"])
def test_primary_button_text_is_readable(name):
    colours = theme(name)
    assert contrast(colours["on-primary"], colours["primary"]) >= 3.0  # large/bold button text (WCAG AA large)
