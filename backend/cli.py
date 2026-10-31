"""Operator commands: `python -m backend.cli seed | create-admin`. Passwords are read with getpass."""
import argparse
from getpass import getpass
from sqlalchemy import select
from backend.config import BOT_KINDS
from backend.database import Session
from backend.models import Admin, Bot, Compatibility
from backend.services.auth import hasher
from backend.services.platforms import PLATFORMS
import storage

LIMITATIONS = ("Openly licensed or public-domain media and direct file links only. Depends on the source site and "
               "the yt-dlp extractor. No private, login-only or DRM media.")


def seed():
    with Session() as db:
        for kind in BOT_KINDS:
            if not db.get(Bot, kind):
                db.add(Bot(id=kind))
        for name, (extractors, _) in [*PLATFORMS.items(), ("direct", (("Generic",), ()))]:
            if not db.get(Compatibility, name):
                db.add(Compatibility(platform=name, extractor=extractors[0], status="NOT VERIFIED", limitations=LIMITATIONS))
        db.commit()
    storage.ensure_bucket()
    print("Seed complete")


def create_admin():
    username = input("Admin username: ").strip()
    password = getpass("Password (at least 12 characters): ")
    if not username or len(username) > 64 or len(password) < 12 or password != getpass("Repeat password: "):
        raise SystemExit("Invalid username or passwords")
    with Session() as db:
        if db.scalar(select(Admin).where(Admin.username == username)):
            raise SystemExit("Admin already exists")
        db.add(Admin(username=username, password_hash=hasher.hash(password)))
        db.commit()
    print("Admin created")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seed", "create-admin"])
    args = parser.parse_args()
    seed() if args.command == "seed" else create_admin()


if __name__ == "__main__":
    main()
