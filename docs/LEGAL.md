# Legal design of the platform

This document explains the decisions that keep the platform within the law and within the terms of the services it
talks to. It is written for operators and reviewers; it is not legal advice.

## What the bots download
- **Supported sources only** (`backend/services/platforms.py`): Wikimedia Commons, the Internet Archive and direct
  links to media files. Social networks and video platforms whose terms forbid downloading (YouTube, Instagram,
  TikTok, Facebook, X, Pinterest and similar) are rejected with a clear message.
- **No circumvention of any kind**: no accounts or cookies of third-party services, no proxy rotation to avoid limits,
  no removal of watermarks or other copyright-management information, no DRM handling. Each source is limited to its
  own yt-dlp extractor, so an embedded player from another site is never followed.
- **Licence shown on every card**: items from the libraries carry the licence published on the source page
  (Creative Commons, public domain, …). Users are reminded to respect it (for example, attribution).
- **Direct links**: the user confirms that they have the right to use the file. The operator should publish terms of
  use (template below) and act on takedown requests.

## File sharing bot
Users upload their own files and get a public link. The operator is a hosting provider for this content:
- publish a contact for abuse and copyright notices (US: designate a DMCA agent with the Copyright Office to rely on
  the 17 U.S.C. §512 safe harbour);
- remove or revoke a file on a valid notice (Dashboard → Files → Revoke/Delete; every action is in the audit log);
- the extension whitelist limits what can be shared; it does not replace an antivirus.

## Personal data
- Stored: Telegram user id, username, first name, language, the jobs and files of the user, payments.
- Not stored: phone numbers, e-mail addresses of bot users, passwords of third-party services.
- Retention: media and uploads are deleted after the configured period (Settings → Limits); the audit log is kept.
- Users can be exported and deleted from the dashboard. Publish a privacy notice (template below) before going live,
  and check local requirements (GDPR in the EU/UK, CCPA/CPRA in California, etc.).

## Payments
Telegram Stars, Stripe and crypto payments are processed by their providers; the platform never sees card data.
Digital goods sold inside Telegram must use Telegram Stars (Telegram's rules for bots).

## Templates to publish before going live
- **Terms of use**: what the bots do; that users may only process content they have the right to use; prohibited
  use (illegal content, malware, infringement); no warranty; how to contact the operator.
- **Privacy notice**: the data listed above, why it is kept, for how long, how to request deletion.
- **Copyright / abuse contact**: an e-mail address and the takedown procedure.
