from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from conda.exceptions import CondaValueError
from conda.models.channel import Channel

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from typing import Any

    from conda.models.records import PackageRecord


@dataclass(frozen=True)
class ChannelChange:
    """A package moving between channels (or with an unknown channel)."""

    name: str
    installed_channel: str
    planned_channel: str


def normalize_channel(channel: object) -> str | None:
    """Return a channel base URL, or None if unusable."""
    if channel is None:
        return None
    raw_channel = str(channel).strip()
    if raw_channel in ("", "<unknown>", "unknown"):
        return None
    return Channel(raw_channel).base_url


def same_channel_url(old_url: str, new_url: str) -> bool:
    """True if URLs match, or are defaults members on the same host."""
    from urllib.parse import urlsplit

    if old_url == new_url:
        return True

    defaults = Channel("defaults").base_urls
    if old_url not in defaults or new_url not in defaults:
        return False

    old, new = urlsplit(old_url), urlsplit(new_url)
    return bool(old.netloc) and old.scheme == new.scheme and old.netloc == new.netloc


def channel_url_from_package_url(url: object) -> str | None:
    """Channel base URL from a package URL, without alias remapping."""
    from conda.base.context import context
    from conda.common.url import split_conda_url_easy_parts

    raw_url = str(url).strip()
    if not raw_url:
        return None
    parts = split_conda_url_easy_parts(context.known_subdirs, raw_url)
    if not parts.scheme or not parts.hostname:
        return None
    netloc = parts.hostname if parts.port is None else f"{parts.hostname}:{parts.port}"
    path = parts.path or ""
    return f"{parts.scheme}://{netloc}{path}".rstrip("/")


def channel_url(*, channel: object = None, url: object = None) -> str | None:
    """Prefer package URL over channel name/URL."""
    if url:
        return channel_url_from_package_url(url)
    return normalize_channel(channel)


def find_channel_changes(
    installed_records: Iterable[PackageRecord],
    planned_packages: Iterable[Mapping[str, Any]],
) -> list[ChannelChange]:
    """Return channel moves and unverifiable (unknown) channel pairs."""
    # display string, concrete URL (None if unknown)
    installed_by_name: dict[str, tuple[str, str | None]] = {}
    for record in installed_records:
        url = channel_url(
            channel=record.channel,
            url=getattr(record, "url", None) or None,
        )
        display = url if url is not None else "<unknown>"
        installed_by_name[record.name] = (display, url)

    changes: list[ChannelChange] = []
    for package in planned_packages:
        name = package["name"]
        if name not in installed_by_name:
            continue  # new package
        planned_raw_channel = package.get("channel") or package.get("base_url")
        planned_url = channel_url(
            channel=planned_raw_channel,
            url=package.get("url"),
        )
        installed_display, installed_url = installed_by_name[name]
        planned_display = planned_url if planned_url is not None else "<unknown>"
        if (
            installed_url
            and planned_url
            and same_channel_url(installed_url, planned_url)
        ):
            continue
        changes.append(
            ChannelChange(
                name=name,
                installed_channel=installed_display,
                planned_channel=planned_display,
            )
        )
    return sorted(changes, key=lambda change: change.name)


def check_solved_channel_changes(
    repodata_fn: str,
    unlink_precs: tuple[PackageRecord, ...],
    link_precs: tuple[PackageRecord, ...],
) -> None:
    """Post-solve hook: warn/confirm on channel changes for `conda self update`."""
    if os.environ.get("CONDA_SELF_CHECK_CHANNEL_CHANGES") != "1":
        return

    planned_packages = [
        {
            "name": record.name,
            "channel": str(record.channel),
            "url": getattr(record, "url", None),
        }
        for record in link_precs
    ]
    changes = find_channel_changes(unlink_precs, planned_packages)
    if not changes:
        return

    def is_unknown(channel: str) -> bool:
        return channel.strip() in ("", "<unknown>", "unknown")

    unknown = [
        change
        for change in changes
        if is_unknown(change.installed_channel) or is_unknown(change.planned_channel)
    ]
    moved = [change for change in changes if change not in unknown]

    if moved:
        print(
            "Warning: this update would move the following packages "
            "to a different channel:",
            file=sys.stderr,
        )
        for change in moved:
            print(
                f"  {change.name}: "
                f"{change.installed_channel} -> {change.planned_channel}",
                file=sys.stderr,
            )

    if unknown:
        print(
            "Warning: the channel is unknown for the following packages, "
            "so it could not be verified:",
            file=sys.stderr,
        )
        for change in unknown:
            print(
                f"  {change.name}: "
                f"{change.installed_channel} -> {change.planned_channel}",
                file=sys.stderr,
            )

    if os.environ.get("CONDA_SELF_ALLOW_CHANNEL_CHANGES") == "1":
        return  # opted in: warn only

    from conda import CondaExitZero
    from conda.base.constants import DEFAULT_CONSOLE_REPORTER_BACKEND
    from conda.base.context import context
    from conda.exceptions import CondaSystemExit
    from conda.reporters import confirm_yn

    if context.dry_run:
        return
    if (
        context.always_yes
        or not sys.stdin.isatty()
        or context.console != DEFAULT_CONSOLE_REPORTER_BACKEND
    ):
        raise CondaValueError(
            "Refusing to move packages to a different channel in "
            "non-interactive mode. Pass --allow-channel-changes to proceed."
        )

    try:
        confirm_yn("Proceed with changing package channels", default="no")
    except CondaSystemExit as exc:
        raise CondaExitZero(str(exc)) from exc
