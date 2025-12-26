from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import fetch_bidtabsdata as fetch  # noqa: E402


class DummyResponse:
    def __init__(self, zip_path: Path):
        self._fh = zip_path.open("rb")

    def iter_content(self, chunk_size: int = 8192):
        while True:
            data = self._fh.read(chunk_size)
            if not data:
                break
            yield data

    def raise_for_status(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._fh.close()


def _build_zip(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("BidTabsData/sample.txt", "hello")


def test_fetch_bidtabsdata_writes_version_and_content(monkeypatch, tmp_path: Path):
    zip_path = tmp_path / "BidTabsData-v0.0.0.zip"
    _build_zip(zip_path)

    captured = {}

    def fake_get(url: str, stream: bool = True, timeout: int = 60):
        captured["url"] = url
        return DummyResponse(zip_path)

    monkeypatch.setenv("BIDTABSDATA_VERSION", "v0.0.0")
    monkeypatch.setenv("BIDTABSDATA_REPO", "example/BidTabsData")
    out_dir = tmp_path / "downloaded"
    monkeypatch.setenv("BIDTABSDATA_OUT_DIR", str(out_dir))
    monkeypatch.setattr(fetch.requests, "get", fake_get)

    dest = fetch.fetch_bidtabsdata()

    assert dest == out_dir
    assert (dest / "sample.txt").read_text() == "hello"
    assert (dest / fetch.VERSION_FILENAME).read_text() == "v0.0.0"
    assert (
        captured["url"]
        == "https://github.com/example/BidTabsData/releases/download/v0.0.0/BidTabsData-v0.0.0.zip"
    )
