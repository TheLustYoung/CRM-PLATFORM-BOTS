# Limitations

## Sources
- Only Wikimedia Commons, the Internet Archive and direct links to media files are accepted. Social networks and video
  platforms whose terms forbid downloading are rejected on purpose (see [LEGAL.md](LEGAL.md)).
- Nothing is fetched with an account or cookies: private, login-only and DRM media stay unavailable.
- Source support depends on the yt-dlp extractors and on changes of the source sites. It is measured with
  `workers.verify` and shown in the dashboard, not guaranteed. Rebuilding the images brings the latest yt-dlp.
- Only formats the extractor reports are offered (audio cut out of a video is MP3).
- User URLs must be HTTP/HTTPS on ports 80/443; private and internal addresses are refused (SSRF protection).

## Telegram limits
- Bots send files up to 50 MB (49 MB configured); larger results go as links. Uploads to the File bot are limited to
  20 MB (19 MB configured) by the standard cloud Bot API. A local Bot API server would lift both limits.
- The bot @username can only be changed in @BotFather. `setMyName` is rate-limited by Telegram.
- Telegram Stars subscriptions always renew every 30 days.

## Operational trade-offs
- Telegram delivery is at-least-once: a crash right after sending but before the database commit may repeat one message.
  Unique request keys and Redis locks prevent duplicate jobs and parallel processing.
- Temporary errors are retried; permanent errors end as `failed`. Reconciliation resumes stuck jobs at most three times.
- Temp-file cleanup assumes workers on one server (horizontal scaling of workers across servers needs shared storage,
  e.g. the S3 backend).
- The extension whitelist and attachment-only delivery do not replace an antivirus.
- No HTTP Range/resume for public downloads; public links are bearer links, revoking does not stop a download already
  in progress.
- A credit spent on a download that later fails is not returned (the daily limit is).
