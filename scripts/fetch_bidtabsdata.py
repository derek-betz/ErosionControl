"""Fetch BidTabsData release assets from GitHub Releases or local sources."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable  # noqa: UP035
from urllib.parse import urlparse

import requests

MACOSX_METADATA_DIR = "__MACOSX"
DEFAULT_HOST = "github.com"
DEFAULT_REPO = "derek-betz/BidTabsData"
DEFAULT_OUT_DIR = Path("data-sample/BidTabsData")
VERSION_FILENAME = ".bidtabsdata_version"
ASSET_PREFIX = "BidTabsData-"
ASSET_SUFFIX = ".zip"
ARCHIVE_ENV = "BIDTABSDATA_ARCHIVE"
URL_ENV = "BIDTABSDATA_URL"
HOST_ENV = "BIDTABSDATA_HOST"
CACHE_DIR_ENV = "BIDTABSDATA_CACHE_DIR"
VERSION_ENV = "BIDTABSDATA_VERSION"


def _asset_name_for_version(version: str) -> str:
    return f"{ASSET_PREFIX}{version}{ASSET_SUFFIX}"


def _download_asset(url: str, dest: Path) -> None:
    try:
        with requests.get(url, stream=True, timeout=60) as response:
            response.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("wb") as fh:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
    except requests.RequestException as exc:
        hint = (
            "Set BIDTABSDATA_ARCHIVE to a local release zip, set BIDTABSDATA_URL to a reachable "
            "mirror, or set BIDTABSDATA_HOST for an internal GitHub host."
        )
        raise SystemExit(f"Failed to download asset: {exc}. {hint}") from exc


def _asset_name_from_url(url: str) -> str | None:
    name = Path(urlparse(url).path).name
    return name or None


def _infer_version_from_asset_name(asset_name: str | None) -> str | None:
    if not asset_name:
        return None
    if asset_name.startswith(ASSET_PREFIX) and asset_name.endswith(ASSET_SUFFIX):
        version = asset_name[len(ASSET_PREFIX) : -len(ASSET_SUFFIX)]
        return version or None
    return None


def _normalize_host(host: str) -> str:
    host = host.strip()
    if host.startswith(("http://", "https://")):
        return host.rstrip("/")
    return f"https://{host}"


def _build_download_url(host: str, repo: str, version: str, asset_name: str) -> str:
    base = _normalize_host(host)
    return f"{base}/{repo}/releases/download/{version}/{asset_name}"


def _first_directory(paths: Iterable[Path]) -> Path | None:
    for path in paths:
        if path.is_dir():
            return path
    return None


def _extract_zip(zip_path: Path, extract_to: Path) -> Path:
    extract_to.mkdir(parents=True, exist_ok=True)
    base = extract_to.resolve()
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.infolist():
                destination = (base / member.filename).resolve()
                if not destination.is_relative_to(base):
                    raise SystemExit(f"Unsafe path in archive: {member.filename}")
                archive.extract(member, path=extract_to)
    except zipfile.BadZipFile as exc:
        raise SystemExit(f"Invalid BidTabsData archive: {exc}") from exc
    entries = [p for p in extract_to.iterdir() if not p.name.startswith(MACOSX_METADATA_DIR)]
    directories = [p for p in entries if p.is_dir()]
    if len(directories) == 1:
        return directories[0]
    preferred = next((p for p in directories if "BidTabsData" in p.name), None)
    if preferred:
        return preferred
    directory = _first_directory(entries)
    return directory or extract_to


def _atomic_replace(src_dir: Path, dest_dir: Path) -> None:
    dest_dir = dest_dir.resolve()
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest_dir.parent) as staging_parent:
        staging_path = Path(staging_parent) / dest_dir.name
        shutil.copytree(src_dir, staging_path)

        backup = dest_dir.parent / f".{dest_dir.name}.bak"
        if backup.exists():
            shutil.rmtree(backup)

        backup_created = False
        if dest_dir.exists():
            dest_dir.rename(backup)
            backup_created = True
        staging_path.replace(dest_dir)
        if backup_created and backup.exists():
            shutil.rmtree(backup)


def fetch_bidtabsdata() -> Path:
    version = os.environ.get(VERSION_ENV)
    repo = os.environ.get("BIDTABSDATA_REPO", DEFAULT_REPO)
    host = os.environ.get(HOST_ENV, DEFAULT_HOST)
    out_dir = Path(os.environ.get("BIDTABSDATA_OUT_DIR", DEFAULT_OUT_DIR))
    archive_override = os.environ.get(ARCHIVE_ENV)
    direct_url = os.environ.get(URL_ENV)
    cache_dir_value = os.environ.get(CACHE_DIR_ENV)

    archive_path: Path | None = None
    asset_name: str | None = None
    if archive_override:
        candidate = Path(archive_override).expanduser()
        if not candidate.is_file():
            raise SystemExit(f"{ARCHIVE_ENV} is set but not a file: {candidate}")
        archive_path = candidate
        asset_name = candidate.name

    if direct_url and not asset_name:
        asset_name = _asset_name_from_url(direct_url)

    if not version:
        version = _infer_version_from_asset_name(asset_name)
    if not version:
        raise SystemExit(
            f"{VERSION_ENV} is required unless {ARCHIVE_ENV} or {URL_ENV} points to a file named "
            f"{ASSET_PREFIX}<version>{ASSET_SUFFIX}."
        )

    if not asset_name:
        asset_name = _asset_name_for_version(version)

    version_file = out_dir / VERSION_FILENAME
    if version_file.exists() and version_file.read_text(encoding="utf-8").strip() == version:
        return out_dir

    cache_path: Path | None = None
    if cache_dir_value:
        cache_dir = Path(cache_dir_value).expanduser()
        if cache_dir.exists() and not cache_dir.is_dir():
            raise SystemExit(f"{CACHE_DIR_ENV} must be a directory: {cache_dir}")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / asset_name

    if not archive_path and cache_path and cache_path.is_file():
        archive_path = cache_path

    download_url: str | None = None
    if not archive_path:
        download_url = direct_url or _build_download_url(host, repo, version, asset_name)

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / asset_name
        if archive_path:
            shutil.copy(archive_path, zip_path)
        else:
            if not download_url:
                raise SystemExit("No download URL resolved for BidTabsData.")
            _download_asset(download_url, zip_path)
            if cache_path and not cache_path.exists():
                shutil.copy(zip_path, cache_path)

        extracted_root = _extract_zip(zip_path, Path(tmpdir) / "extracted")
        (extracted_root / VERSION_FILENAME).write_text(version, encoding="utf-8")
        _atomic_replace(extracted_root, out_dir)
        return out_dir


def main() -> None:
    try:
        dest = fetch_bidtabsdata()
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        raise
    else:
        print(f"BidTabsData downloaded to: {dest}")


if __name__ == "__main__":
    main()
