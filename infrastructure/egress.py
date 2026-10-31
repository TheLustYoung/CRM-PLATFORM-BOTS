"""HTTP/CONNECT proxy with DNS pinning (SSRF protection for the workers). Run only on a private Docker network.

Every outgoing request of the workers passes here: the host is resolved once, every address must be public, and the
connection goes to that checked address only. Ports other than 80/443 and URLs with credentials are refused.
"""
import logging
import select
import socket
import socketserver
import threading
from urllib.parse import urlsplit
from backend.services.security import public_addresses, normalize_url

slots = threading.BoundedSemaphore(64)
log = logging.getLogger("egress")


def open_upstream(host: str, port: int) -> socket.socket:
    """Connect to the first reachable checked address, IPv4 first.

    Docker networks usually have no IPv6 while many sites publish IPv6 addresses too, so IPv4 is tried first.
    Only numeric, already validated addresses are used, so there is no second hostname lookup.
    """
    addresses = sorted(public_addresses(host, port), key=lambda a: ":" in a)
    last_error: OSError | None = None
    for address in addresses:
        try:
            return socket.create_connection((address, port), timeout=25)
        except OSError as error:
            last_error = error
    raise last_error or OSError("no address")


class Handler(socketserver.StreamRequestHandler):
    timeout = 30

    def handle(self):
        if not slots.acquire(blocking=False):
            return
        try:
            self.forward()
        except Exception as error:
            # Host only (never the path or query): enough to diagnose without logging user data.
            log.warning('{"event":"egress_refused","host":"%s","error":"%s: %s"}', getattr(self, "host", "?"),
                        type(error).__name__, str(error)[:120])
            try:
                self.wfile.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            except OSError:
                pass
        finally:
            slots.release()

    def forward(self):
        line = self.rfile.readline(8193)
        if len(line) > 8192:
            return
        method, target, version = line.decode("ascii").strip().split(" ")
        headers = []
        length = 0
        while True:
            header = self.rfile.readline(8193)
            length += len(header)
            if length > 32768 or not header:
                raise ValueError()
            if header == b"\r\n":
                break
            headers.append(header)
        if method == "CONNECT":
            parsed = urlsplit("https://" + target)
            port = parsed.port or 443
        else:
            normalized = normalize_url(target, resolve=False)
            parsed = urlsplit(normalized)
            if parsed.scheme != "http":
                raise ValueError()
            port = parsed.port or 80
        self.host = parsed.hostname
        if port not in {80, 443} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("port or credentials not allowed")
        with open_upstream(parsed.hostname, port) as upstream:
            if method == "CONNECT":
                self.wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                self.wfile.flush()
            else:
                path = parsed.path or "/"
                if parsed.query:
                    path += "?" + parsed.query
                upstream.sendall(f"{method} {path} HTTP/1.1\r\n".encode("ascii"))
                for header in headers:
                    if header.lower().startswith((b"proxy-", b"connection:", b"host:")):
                        continue
                    upstream.sendall(header)
                upstream.sendall(f"Host: {parsed.netloc}\r\nConnection: close\r\n\r\n".encode("ascii"))
                # Read body from the buffered reader, avoiding loss of pre-buffered bytes.
                lengths = [h.split(b":", 1)[1].strip() for h in headers if h.lower().startswith(b"content-length:")]
                if any(h.lower().startswith(b"transfer-encoding:") for h in headers):
                    raise ValueError("Chunked request bodies are not accepted")
                remaining = int(lengths[0]) if len(lengths) == 1 else 0
                if remaining < 0 or remaining > 10_000_000 or len(lengths) > 1:
                    raise ValueError()
                while remaining:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        raise ValueError()
                    upstream.sendall(chunk)
                    remaining -= len(chunk)
            while True:
                readable, _, _ = select.select([self.connection, upstream], [], [], 60)
                if not readable:
                    break
                for source in readable:
                    chunk = source.recv(65536)
                    if not chunk:
                        return
                    (upstream if source is self.connection else self.connection).sendall(chunk)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with Server(("0.0.0.0", 3128), Handler) as server:
        server.serve_forever()
