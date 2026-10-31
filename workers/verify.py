"""Measured source compatibility, shown in the admin panel.

    python -m workers.verify --case archive video https://archive.org/details/... --case wikimedia image https://commons.wikimedia.org/wiki/File:...

Each sample is really extracted and downloaded (smallest format, <= 50 MB) through the same
adapter the bots use. Results go to the platform_compatibility table shown in the admin panel.
Statuses: VERIFIED, PARTIAL, TEMPORARILY UNAVAILABLE, UNSUPPORTED.
"""
import argparse
import tempfile
from dataclasses import dataclass
from pathlib import Path
from yt_dlp.utils import DownloadError
from backend.database import Session
from backend.models import Compatibility, now
from backend.services.platforms import PLATFORMS, platform_for
from backend.services.security import DomainError
from workers.adapters import MediaAdapter
from workers.tasks import download_error_code

SAMPLE_LIMIT = 50_000_000
EXTRACTORS = {**{name: extractors[0] for name, (extractors, _) in PLATFORMS.items()}, "direct": "Generic"}


@dataclass
class Sample:
    platform: str
    label: str
    url: str
    ok: bool = False
    code: str = ""
    detail: str = ""


def check(sample: Sample, adapter: MediaAdapter | None = None) -> Sample:
    adapter = adapter or MediaAdapter()
    try:
        if platform_for(sample.url) != sample.platform:
            raise DomainError("platform_mismatch")
        info = adapter.extract(sample.url)
        chosen = min(info["formats"], key=lambda f: f.get("size") or SAMPLE_LIMIT)
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
            files = adapter.download(sample.url, chosen["selector"], Path(temp), SAMPLE_LIMIT, chosen.get("merge"))
            size = sum(f.stat().st_size for f in files)
        sample.ok = bool(files) and size > 0
        sample.detail = f"{len(files)} file(s), {size // 1000} KB, {chosen['label']}"
    except DownloadError as exc:
        sample.code = download_error_code(exc)
    except DomainError as exc:
        sample.code = str(exc)
    except Exception as exc:  # network and provider failures: record the class, never the provider text
        sample.code = f"error:{type(exc).__name__}"
    return sample


def status_for(samples: list[Sample]) -> str:
    passed = sum(s.ok for s in samples)
    if passed == len(samples):
        return "VERIFIED"
    if passed:
        return "PARTIAL"
    if all(s.code in {"login_required", "no_media", "unsupported"} for s in samples):
        return "UNSUPPORTED"
    return "TEMPORARILY UNAVAILABLE"


def summary(samples: list[Sample]) -> str:
    lines = [f"{'OK' if s.ok else 'FAIL'} {s.label}: {s.detail if s.ok else s.code}" for s in samples]
    return f"{sum(s.ok for s in samples)}/{len(samples)} samples passed. " + "; ".join(lines)


def record(results: dict[str, list[Sample]]) -> None:
    with Session() as db:
        for platform, samples in results.items():
            db.merge(Compatibility(platform=platform, extractor=EXTRACTORS.get(platform, platform), status=status_for(samples),
                                   last_test_date=now(), limitations=summary(samples)[:2000]))
        db.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", nargs=3, action="append", metavar=("PLATFORM", "LABEL", "URL"), required=True)
    parser.add_argument("--dry-run", action="store_true", help="print results without writing to the database")
    args = parser.parse_args()
    results: dict[str, list[Sample]] = {}
    for platform, label, url in args.case:
        sample = check(Sample(platform, label, url))
        results.setdefault(platform, []).append(sample)
        print(f"{platform:10} {label:14} {'OK  ' + sample.detail if sample.ok else 'FAIL ' + sample.code}")
    for platform, samples in results.items():
        print(f"=> {platform}: {status_for(samples)}")
    if not args.dry_run:
        record(results)


if __name__ == "__main__":
    main()
