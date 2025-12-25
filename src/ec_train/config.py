"""Configuration helpers for EC Train workflows."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_ERMS_URL = "https://erms12c.indot.in.gov/viewdocs/Default.aspx"


@dataclass(slots=True)
class Config:
    """Configuration for locating data sources and credentials."""

    cost_estimate_checkout: Path | None = None
    bidtabs_path: Path | None = None
    erms_url: str = DEFAULT_ERMS_URL
    download_dir: Path = field(default_factory=lambda: Path.cwd() / "ec_train_downloads")
    cookie_jar: Path | None = None
    username: str | None = None
    password: str | None = None
    cookies: MutableMapping[str, str] | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        """Create a config instance from environment variables."""
        env = env or os.environ
        cost_checkout = cls._optional_path(env.get("EC_TRAIN_COST_CHECKOUT"))
        bidtabs = cls._optional_path(env.get("EC_TRAIN_BIDTABS_PATH"))
        download_dir = (
            cls._optional_path(env.get("EC_TRAIN_DOWNLOAD_DIR"))
            or Path.cwd() / "ec_train_downloads"
        )
        cookie_jar = cls._optional_path(env.get("EC_TRAIN_COOKIE_JAR"))
        username = env.get("EC_TRAIN_USERNAME")
        password = env.get("EC_TRAIN_PASSWORD")
        cookies = cls._parse_cookie_kv(env.get("EC_TRAIN_COOKIES"))

        return cls(
            cost_estimate_checkout=cost_checkout,
            bidtabs_path=bidtabs,
            download_dir=download_dir,
            cookie_jar=cookie_jar,
            username=username,
            password=password,
            cookies=cookies,
        )

    @staticmethod
    def _optional_path(value: str | None) -> Path | None:
        if not value:
            return None
        return Path(value).expanduser()

    @staticmethod
    def _parse_cookie_kv(raw: str | None) -> MutableMapping[str, str] | None:
        if not raw:
            return None
        cookies: dict[str, str] = {}
        parts: Iterable[str] = raw.split(";")
        for part in parts:
            if "=" not in part:
                continue
            name, value = part.split("=", 1)
            cookies[name.strip()] = value.strip()
        return cookies


__all__ = ["Config", "DEFAULT_ERMS_URL"]
