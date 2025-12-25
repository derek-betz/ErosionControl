"""ERMS scraping utilities."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)
USER_AGENT = "EC-Train/0.1 (+https://github.com/derek-betz/ErosionControl)"


@dataclass(slots=True)
class DocumentLink:
    """A single document fetched from ERMS."""

    name: str
    url: str
    path: Path


class ERMSFetcher:
    """Fetch documents from ERMS with retry and cookie persistence."""

    def __init__(
        self,
        base_url: str,
        download_dir: Path,
        cookies: MutableMapping[str, str] | None = None,
        cookie_jar: Path | None = None,
        username: str | None = None,
        password: str | None = None,
        max_retries: int = 3,
        backoff_seconds: float = 1.5,
        headless: bool = False,
    ) -> None:
        self.base_url = base_url
        self.download_dir = download_dir
        self.cookies = cookies or {}
        self.cookie_jar = cookie_jar
        self.username = username
        self.password = password
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.headless = headless
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        if self.cookies:
            self.session.cookies.update(self.cookies)
        if self.cookie_jar and self.cookie_jar.exists():
            self.session.cookies.update(self._load_cookie_file(self.cookie_jar))

    def _load_cookie_file(self, path: Path) -> Mapping[str, str]:
        try:
            with path.open() as f:
                raw = f.read()
            cookies: dict[str, str] = {}
            for pair in raw.split(";"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    cookies[k.strip()] = v.strip()
            return cookies
        except OSError:
            LOGGER.warning("Unable to read cookie jar at %s", path)
            return {}

    def _save_cookie_file(self) -> None:
        if not self.cookie_jar:
            return
        self.cookie_jar.parent.mkdir(parents=True, exist_ok=True)
        cookie_str = "; ".join(f"{k}={v}" for k, v in self.session.cookies.items())
        self.cookie_jar.write_text(cookie_str)

    def _get(self, url: str, **kwargs) -> requests.Response:
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(url, **kwargs)
                if "captcha" in resp.text.lower() or "login" in resp.url.lower():
                    raise RuntimeError(
                        "ERMS responded with a login or CAPTCHA page. Manual intervention required."
                    )
                resp.raise_for_status()
                return resp
            except Exception as exc:  # noqa: BLE001
                if attempt == self.max_retries:
                    raise
                sleep_time = self.backoff_seconds * attempt
                LOGGER.warning("Request failed (%s). Retrying in %.1fs", exc, sleep_time)
                time.sleep(sleep_time)
        raise RuntimeError("Unreachable")

    def search_contract(self, contract: str) -> str | None:
        """Return the URL for the contract folder if found."""
        resp = self._get(self.base_url, params={"searchText": contract})
        soup = BeautifulSoup(resp.text, "html.parser")
        link = soup.find("a", href=True, string=lambda text: text and contract in text)
        if not link:
            LOGGER.info("Contract %s not found in ERMS search.", contract)
            return None
        return urljoin(self.base_url, link["href"])

    def list_documents(self, folder_url: str) -> list[DocumentLink]:
        """Enumerate documents from a contract folder."""
        resp = self._get(folder_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        docs: list[DocumentLink] = []
        for link in soup.find_all("a", href=True):
            name = link.text.strip()
            if not name:
                continue
            href = urljoin(folder_url, link["href"])
            docs.append(
                DocumentLink(
                    name=name,
                    url=href,
                    path=self.download_dir / name.replace("/", "_"),
                )
            )
        return docs

    def download_documents(
        self, docs: Iterable[DocumentLink], patterns: Iterable[str]
    ) -> list[DocumentLink]:
        """Download documents that match any of the provided patterns."""
        self.download_dir.mkdir(parents=True, exist_ok=True)
        selected: list[DocumentLink] = []
        for doc in docs:
            lower_name = doc.name.lower()
            if not any(pattern.lower() in lower_name for pattern in patterns):
                continue
            LOGGER.info("Downloading %s", doc.name)
            resp = self._get(doc.url)
            doc.path.write_bytes(resp.content)
            selected.append(doc)
        self._save_cookie_file()
        return selected


__all__ = ["DocumentLink", "ERMSFetcher"]
