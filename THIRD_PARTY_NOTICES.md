# Third-party components

The project's own code is covered by [LICENSE](LICENSE). It depends on the open-source components below, each under
its own licence. They are installed from their official package registries and are not modified.

| Component | Used for | Licence |
|---|---|---|
| FastAPI, Starlette, Pydantic | HTTP API, validation | MIT |
| SQLAlchemy, Alembic | Database access, migrations | MIT |
| psycopg | PostgreSQL driver | LGPL-3.0 (used as an unmodified library) |
| Celery, Redis client (redis-py) | Background jobs, queues | BSD-3-Clause / MIT |
| aiogram | Telegram Bot API framework | MIT |
| yt-dlp | Reading media from the supported sources | Unlicense (public domain) |
| FFmpeg (Debian package in the Docker image) | Merging separate video and audio streams | LGPL-2.1+ / GPL-2.0+ (separate program, invoked as a process) |
| boto3 | S3-compatible storage | Apache-2.0 |
| httpx | Outgoing HTTP | BSD-3-Clause |
| argon2-cffi, PyJWT, cryptography, pyotp | Password hashing, sessions, encryption, 2FA | MIT / MIT / Apache-2.0 or BSD / MIT |
| sentry-sdk | Optional error tracking | MIT |
| React, React DOM | Dashboard UI | MIT |
| Vite, TypeScript | Dashboard build | MIT / Apache-2.0 |
| Inter, Geist (via @fontsource) | Dashboard fonts | SIL Open Font License 1.1 |

Full licence texts ship with each package (`pip show -f <package>`, `node_modules/<package>/LICENSE`).
Telegram, Wikimedia Commons and the Internet Archive are trademarks of their owners; the project is not affiliated
with or endorsed by them.
