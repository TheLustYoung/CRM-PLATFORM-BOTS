import socket
import pytest
from backend.config import settings
from backend.services.security import DomainError
from workers import adapters


def no_dns(*_, **__):
    raise socket.gaierror("no DNS on the private Docker network")


def test_worker_behind_egress_proxy_needs_no_dns(monkeypatch):
    # In Docker the worker has no DNS; the egress proxy resolves and checks the host instead.
    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    monkeypatch.setattr(settings(), "egress_proxy", "http://egress:3128")
    assert adapters.checked_url("https://archive.org/details/x") == "https://archive.org/details/x"
    with pytest.raises(DomainError):
        adapters.checked_url("http://127.0.0.1/")  # literal private addresses are still refused


def test_worker_without_proxy_checks_dns_itself(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", no_dns)
    monkeypatch.setattr(settings(), "egress_proxy", "")
    with pytest.raises(DomainError):
        adapters.checked_url("https://archive.org/details/x")
