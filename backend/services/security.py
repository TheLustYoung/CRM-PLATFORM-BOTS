import ipaddress
import re
import socket
from urllib.parse import urlsplit, urlunsplit


class DomainError(ValueError):
    """Public error code (a locale key); never contains provider output or credentials."""


def public_addresses(host: str, port: int) -> list[str]:
    try:
        addresses = list({row[4][0] for row in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
    except (OSError, UnicodeError):
        raise DomainError("invalid_url") from None
    if not addresses or any(not is_public_ip(a) for a in addresses):
        raise DomainError("invalid_url")
    return addresses


def is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return ip.is_global and not (ip.is_multicast or ip.is_reserved or ip.is_unspecified or ip.is_loopback or ip.is_link_local)


def normalize_url(value: str, resolve: bool = True) -> str:
    """Accept only public http(s) URLs on default ports; blocks SSRF to internal services."""
    if len(value) > 2048 or any(ord(c) < 33 for c in value) or "\\" in value:
        raise DomainError("invalid_url")
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError()
        host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port not in {80, 443} or host in {"localhost", "metadata.google.internal"}:
            raise ValueError()
        try:
            ipaddress.ip_address(host)
            if not is_public_ip(host):
                raise DomainError("invalid_url")
        except ValueError as error:
            if isinstance(error, DomainError):
                raise
        if resolve:
            public_addresses(host, port)
        authority = f"[{host}]" if ":" in host else host
        if parsed.port:
            authority += f":{port}"
        return urlunsplit((parsed.scheme, authority, parsed.path or "/", parsed.query, ""))
    except (ValueError, UnicodeError):
        raise DomainError("invalid_url") from None


def _fernet():
    """Symmetric key for secrets stored in the database (bot tokens, e-mail API key), derived from JWT_SECRET."""
    import base64
    import hashlib
    from cryptography.fernet import Fernet
    from backend.config import settings
    key = hashlib.sha256(b"stored-secrets|" + settings().jwt_secret.get_secret_value().encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(text: str) -> str:
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token: str | None) -> str | None:
    """None when there is nothing stored or the server secret changed (the administrator enters the value again)."""
    from cryptography.fernet import InvalidToken
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None


def safe_filename(name: str) -> str:
    """Keep Unicode letters (Arabic, Cyrillic, ...) but strip paths and control characters."""
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[^\w.() -]", "_", name, flags=re.UNICODE).strip(" .")
    return name[:180] or "file.bin"


ALLOWED_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".mov", ".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac",
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf", ".txt", ".zip", ".rar", ".7z",
    ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".csv",
}
