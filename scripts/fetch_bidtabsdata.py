"""Fetch BidTabsData release assets from GitHub Releases."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable  # noqa: UP035

import requests

MACOSX_METADATA_DIR = "__MACOSX"
DEFAULT_REPO = "derek-betz/BidTabsData"
DEFAULT_OUT_DIR = Path("data-sample/BidTabsData")
VERSION_FILENAME = ".bidtabsdata_version"
ASSET_PREFIX = "BidTabsData-"
ASSET_SUFFIX = ".zip"


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} environment variable is required.")
    return value


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
        raise SystemExit(f"Failed to download asset: {exc}") from exc


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
    version = _require_env("BIDTABSDATA_VERSION")
    repo = os.environ.get("BIDTABSDATA_REPO", DEFAULT_REPO)
    out_dir = Path(os.environ.get("BIDTABSDATA_OUT_DIR", DEFAULT_OUT_DIR))

    asset_name = f"{ASSET_PREFIX}{version}{ASSET_SUFFIX}"
    download_url = f"https://github.com/{repo}/releases/download/{version}/{asset_name}"

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / asset_name
        _download_asset(download_url, zip_path)

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
