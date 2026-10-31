import io
import socket
import unittest
from unittest.mock import MagicMock, patch
import pytest
from infrastructure import egress
from infrastructure.egress import Handler
from backend.services.security import DomainError


class EgressTests(unittest.TestCase):
    def handler(self, request):
        handler = Handler.__new__(Handler)
        handler.rfile = io.BytesIO(request)
        handler.wfile = io.BytesIO()
        handler.connection = MagicMock()
        return handler

    def test_connect_pins_validated_ip(self):
        handler = self.handler(b"CONNECT cdn.example:443 HTTP/1.1\r\nHost: cdn.example\r\n\r\n")
        with patch("infrastructure.egress.public_addresses", return_value=["8.8.8.8"]), patch("infrastructure.egress.socket.create_connection") as connect, patch("infrastructure.egress.select.select", return_value=([], [], [])):
            handler.forward()
            connect.assert_called_once_with(("8.8.8.8", 443), timeout=25)
        self.assertIn(b"200 Connection Established", handler.wfile.getvalue())

    def test_internal_destination_never_connects(self):
        handler = self.handler(b"CONNECT localhost:443 HTTP/1.1\r\n\r\n")
        with patch("infrastructure.egress.public_addresses", side_effect=DomainError("invalid_url")), patch("infrastructure.egress.socket.create_connection") as connect:
            with self.assertRaises(DomainError):
                handler.forward()
            connect.assert_not_called()

    def test_forbidden_port_never_connects(self):
        handler = self.handler(b"CONNECT example.com:6379 HTTP/1.1\r\n\r\n")
        with patch("infrastructure.egress.socket.create_connection") as connect:
            with self.assertRaises(ValueError):
                handler.forward()
            connect.assert_not_called()


def test_prefers_ipv4_and_skips_unreachable_addresses(monkeypatch):
    # Docker without IPv6: the IPv6 address fails instantly, the proxy must still connect over IPv4.
    monkeypatch.setattr(egress, "public_addresses", lambda host, port: ["2a00:1450:4001:80b::200e", "142.250.185.78"])
    tried = []

    def connect(address, timeout):
        tried.append(address[0])
        if ":" in address[0]:
            raise OSError("Network is unreachable")
        return "connected"

    monkeypatch.setattr(socket, "create_connection", connect)
    assert egress.open_upstream("www.example.org", 443) == "connected"
    assert tried == ["142.250.185.78"]  # IPv4 first


def test_falls_back_to_the_next_address_and_reports_the_last_error(monkeypatch):
    monkeypatch.setattr(egress, "public_addresses", lambda host, port: ["1.1.1.1", "8.8.8.8"])
    tried = []

    def connect(address, timeout):
        tried.append(address[0])
        if address[0] == "1.1.1.1":
            raise OSError("timed out")
        return "connected"

    monkeypatch.setattr(socket, "create_connection", connect)
    assert egress.open_upstream("example.com", 443) == "connected" and tried == ["1.1.1.1", "8.8.8.8"]

    monkeypatch.setattr(socket, "create_connection", lambda address, timeout: (_ for _ in ()).throw(OSError("down")))
    with pytest.raises(OSError, match="down"):
        egress.open_upstream("example.com", 443)
