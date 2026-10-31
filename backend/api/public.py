"""Public download links: a branded multilingual page and a direct download URL."""
import html
import logging
from urllib.parse import quote
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import update
from backend.database import session
from backend.models import Bot, UploadedFile, aware
from backend.services import i18n
from backend.services.limits import rate_limit
from backend.services.security import DomainError
import storage

router = APIRouter(tags=["public"])
log = logging.getLogger(__name__)
SECURITY_HEADERS = {"X-Content-Type-Options": "nosniff", "Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


def human_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1000 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1000


def page_language(request: Request) -> str:
    choice = request.query_params.get("lang")
    if choice in i18n.catalogs():
        return choice
    for part in request.headers.get("accept-language", "").split(","):
        base = part.split(";")[0].strip().lower().replace("_", "-").split("-")[0]
        if base in i18n.catalogs():
            return base
    return i18n.FALLBACK


def render(lang: str, body: str, status: int = 200) -> HTMLResponse:
    t = lambda key: html.escape(i18n.raw(lang, key))
    direction = "rtl" if i18n.is_rtl(lang) else "ltr"
    switch = " · ".join(f'<a href="?lang={code}">{html.escape(name)}</a>' for code, name in i18n.languages().items())
    page = f"""<!doctype html><html lang="{lang}" dir="{direction}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>{t('page_title')}</title><style>
body{{margin:0;font-family:system-ui,-apple-system,"Segoe UI",Tahoma,sans-serif;background:#0f1d1c;color:#eef5f2;min-height:100vh;display:grid;place-items:center}}
main{{width:min(440px,calc(100% - 32px));background:#16302e;border:1px solid #2a4a47;border-radius:18px;padding:28px}}
h1{{font-size:20px;margin:0 0 18px;word-break:break-word}}dl{{display:grid;grid-template-columns:auto 1fr;gap:8px 16px;margin:0 0 22px}}
dt{{color:#8fb3ad}}dd{{margin:0;unicode-bidi:plaintext}}a.button{{display:block;text-align:center;background:#5ee0b6;color:#0b1716;font-weight:700;
padding:14px;border-radius:12px;text-decoration:none}}footer{{margin-top:18px;font-size:13px;color:#8fb3ad;text-align:center}}footer a{{color:#8fb3ad}}
</style></head><body><main>{body}<footer>{switch}</footer></main></body></html>"""
    return HTMLResponse(page, status_code=status, headers={**SECURITY_HEADERS,
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"})


@router.get("/go/{ad_id}/{job_id}")
def ad_redirect(ad_id: str, job_id: str, request: Request, db=Depends(session)):
    """The button of a sponsored message: counts the click (once per download), then opens the advertiser's page."""
    from fastapi.responses import RedirectResponse
    from backend.services import monetization
    try:
        rate_limit(f"go:{request.client.host}", 60, 60)
    except DomainError:
        return render(page_language(request), "<h1>429</h1>", 429)
    target = monetization.ad_click(db, ad_id[:36], job_id[:40]) if len(ad_id) <= 36 else None
    if not target:
        return render(page_language(request), f"<h1>{html.escape(i18n.raw(page_language(request), 'page_not_found'))}</h1>", 404)
    return RedirectResponse(target, status_code=302, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


@router.get("/f/{token}", response_class=HTMLResponse)
def file_page(token: str, request: Request, db=Depends(session)):
    lang = page_language(request)
    try:
        if len(token) > 64:
            raise DomainError("not_found")
        rate_limit(f"public:{request.client.host}", 120, 60)
        file = storage.resolve_link(db, token)
    except DomainError:
        return render(lang, f"<h1>{html.escape(i18n.raw(lang, 'page_not_found'))}</h1>", 404)
    bot = db.get(Bot, file.bot_id) if file.bot_id else None
    t = lambda key: html.escape(i18n.raw(lang, key))
    rows = [(t("page_size"), human_size(file.size)), (t("page_type"), html.escape(file.mime)),
            (t("page_uploaded"), aware(file.created_at).date().isoformat())]
    if aware(file.expires_at).year < 2099:  # permanent links (set in the dashboard) show no expiry date
        rows.append((t("page_expires"), aware(file.expires_at).date().isoformat()))
    if bot and bot.username:
        rows.append((t("page_shared_by"), f"@{html.escape(bot.username)}"))
    details = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    body = f'<h1 dir="auto">{html.escape(file.name)}</h1><dl>{details}</dl><a class="button" href="/f/{quote(token)}/download">⬇ {t("page_download")}</a>'
    return render(lang, body)


@router.get("/f/{token}/download")
def file_download(token: str, request: Request, db=Depends(session)):
    lang = page_language(request)
    try:
        if len(token) > 64:
            raise DomainError("not_found")
        rate_limit(f"public:{request.client.host}", 120, 60)
        file = storage.resolve_link(db, token)
    except DomainError:
        return render(lang, f"<h1>{html.escape(i18n.raw(lang, 'page_not_found'))}</h1>", 404)
    try:
        body, close = storage.open_object(file.object_key)
    except storage.ObjectMissing:
        # Database and storage disagree (object removed outside the platform): a clear page, never a 500.
        log.warning('{"event":"object_missing","file_id":"%s"}', file.id)
        return render(lang, f"<h1>{html.escape(i18n.raw(lang, 'page_file_missing'))}</h1>", 404)
    db.execute(update(UploadedFile).where(UploadedFile.id == file.id).values(downloads=UploadedFile.downloads + 1))
    db.commit()

    def chunks():
        try:
            yield from body
        finally:
            close()
    # Always served as an attachment: uploaded HTML/SVG can never execute on our domain.
    return StreamingResponse(chunks(), media_type="application/octet-stream", headers={**SECURITY_HEADERS,
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(file.name)}", "Content-Length": str(file.size),
        "Content-Security-Policy": "default-src 'none'; sandbox"})
