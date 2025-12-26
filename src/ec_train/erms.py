"""ERMS scraping utilities."""

from __future__ import annotations

import logging
import re
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
        self._results_cache: dict[str, str] = {}
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
        search_term = _contract_search_term(contract)
        resp = self._post_contract_search(search_term)
        docs = _extract_view_links(resp.text, self.base_url, download_dir=self.download_dir)
        if not docs:
            LOGGER.info("Contract %s not found in ERMS search.", contract)
            return None
        self._results_cache[resp.url] = resp.text
        return resp.url

    def list_documents(self, folder_url: str) -> list[DocumentLink]:
        """Enumerate documents from a contract folder."""
        cached = self._results_cache.get(folder_url)
        if cached is not None:
            return _extract_view_links(cached, self.base_url, download_dir=self.download_dir)
        resp = self._get(folder_url)
        return _extract_view_links(resp.text, self.base_url, download_dir=self.download_dir)

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
            filename = _filename_from_response(resp)
            if filename:
                doc.path = self.download_dir / _sanitize_filename(filename)
            doc.path.write_bytes(resp.content)
            selected.append(doc)
        self._save_cookie_file()
        return selected

    def _post_contract_search(self, contract_number: str) -> requests.Response:
        resp = self._get(self.base_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        payload: dict[str, str] = {}
        for inp in soup.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            payload[name] = inp.get("value") or ""
        payload["ctl00$body$ContractNumberTextBox"] = contract_number
        payload["ctl00$body$FindDocumentsByContractNumber"] = "Find Documents"
        select = soup.find("select", attrs={"name": "ctl00$body$DocumentTypeDropDown"})
        if select and select.find("option"):
            payload[select["name"]] = select.find("option").get("value") or "All"
        post = self.session.post(self.base_url, data=payload)
        if "captcha" in post.text.lower() or "login" in post.url.lower():
            raise RuntimeError(
                "ERMS responded with a login or CAPTCHA page. Manual intervention required."
            )
        post.raise_for_status()
        return post


__all__ = ["DocumentLink", "ERMSFetcher"]


def _contract_search_term(contract: str) -> str:
    match = re.search(r"\b(\d{5})\b", contract)
    if match:
        return match.group(1)
    digits = re.findall(r"\d+", contract)
    if not digits:
        return contract
    for chunk in digits:
        if len(chunk) >= 5:
            return chunk[-5:]
    return digits[0]


def _extract_view_links(
    html: str, base_url: str, download_dir: Path | None = None
) -> list[DocumentLink]:
    soup = BeautifulSoup(html, "html.parser")
    docs: list[DocumentLink] = []
    for inp in soup.find_all("input"):
        onclick = inp.get("onclick") or ""
        match = re.search(r"View12\.aspx\?Id=\d+", onclick)
        if not match:
            continue
        href = urljoin(base_url, match.group(0))
        row = inp.find_parent("tr")
        name = None
        if row:
            cells = row.find_all("td")
            if len(cells) >= 3:
                name = cells[2].get_text(strip=True)
        if not name:
            name = match.group(0).replace("View12.aspx?Id=", "Document_")
        safe_name = _sanitize_filename(name)
        doc_path = (download_dir or Path.cwd()) / safe_name
        docs.append(DocumentLink(name=name, url=href, path=doc_path))
    return docs


def _filename_from_response(resp: requests.Response) -> str | None:
    header = resp.headers.get("content-disposition")
    if not header:
        return None
    match = re.search(r"filename=\"?([^\";]+)\"?", header, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[\\\\/:*?\"<>|]", "_", name).strip()
    return cleaned or "document"
