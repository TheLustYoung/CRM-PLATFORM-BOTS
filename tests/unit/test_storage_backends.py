import pytest
from storage import backends


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setattr(backends.settings(), "storage_backend", "local")
    monkeypatch.setattr(backends.settings(), "storage_dir", str(tmp_path / "files"))
    store = backends.backend()
    store.ensure()
    return store


def test_local_backend_roundtrip(local, tmp_path):
    source = tmp_path / "отчёт.txt"
    source.write_bytes(b"payload")
    assert local.upload(source, "jobs/1/отчёт.txt", "text/plain") == 7
    chunks, close = local.open("jobs/1/отчёт.txt")
    assert b"".join(chunks) == b"payload"
    close()
    local.delete("jobs/1/отчёт.txt")
    local.delete("jobs/1/отчёт.txt")  # deleting twice is harmless
    with pytest.raises(backends.ObjectMissing):
        local.open("jobs/1/отчёт.txt")


def test_local_backend_blocks_path_traversal(local):
    with pytest.raises(ValueError):
        local.path("../outside.txt")
