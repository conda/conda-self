from __future__ import annotations

import os
import sys

from dataclasses import dataclass
from typing import TYPE_CHECKING

from conda.models.channel import Channel
from conda.exceptions import CondaValueError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from typing import Any

    from conda.models.records import PrefixRecord, PackageRecord


@dataclass(frozen=True)
class ChannelChange:
    """A package whose planned replacement comes from another channel."""

    name: str
    installed_channel: str  # channel of the installed package, as recorded
    planned_channel: str  # channel of the planned package, as solved


def normalize_channel(channel: object) -> str | None:
    """Return a normalized channel value for comparison, or None if unusable.

    Normalizing lets differently written forms of the same channel compare
    equal, e.g. "conda-forge" and "https://conda.anaconda.org/conda-forge".
    """
    if channel is None:
        return None
    raw_channel = str(channel).strip()
    if raw_channel in ("", "<unknown>", "unknown"):
        return None
    parsed_channel = Channel(raw_channel)
    # 'defaults' is one configured channel that expands to pkgs/main,
    # pkgs/r, ... — treat the whole family as one channel.
    if parsed_channel.canonical_name == "defaults":
        return "defaults"
    return parsed_channel.base_url or parsed_channel.canonical_name or raw_channel


def find_channel_changes(
    installed_records: Iterable[PrefixRecord],
    planned_packages: Iterable[Mapping[str, Any]],
) -> list[ChannelChange]:
    """Return packages whose planned channel differs from the installed one."""
    # Map each installed package name to its channel in two forms:
    # the raw form for display, and the normalized form for comparison.
    installed_by_name: dict[str, tuple[str, str]] = {}
    for record in installed_records:
        raw_channel = str(record.channel)
        normalized_channel = normalize_channel(record.channel)
        if normalized_channel is not None:
            installed_by_name[record.name] = (raw_channel, normalized_channel)

    changes: list[ChannelChange] = []
    for package in planned_packages:
        name = package["name"]
        if name not in installed_by_name:
            continue  # newly installed package: out of scope for the ticket
        planned_raw_channel = package.get("channel") or package.get("base_url")
        planned_normalized_channel = normalize_channel(planned_raw_channel)
        if planned_normalized_channel is None:
            continue
        installed_raw_channel, installed_normalized_channel = installed_by_name[name]
        if planned_normalized_channel != installed_normalized_channel:
            changes.append(
                ChannelChange(
                    name=name,
                    installed_channel=installed_raw_channel,
                    planned_channel=str(planned_raw_channel),
                )
            )
    return sorted(changes, key=lambda change: change.name)


def check_solved_channel_changes(
    repodata_fn: str,
    unlink_precs: tuple[PackageRecord, ...],
    link_precs: tuple[PackageRecord, ...],
) -> None:
    """Check a solved transaction for channel changes (post-solve hook)."""
    # Only active for `conda self update`, which sets this on the subprocess.
    if os.environ.get("CONDA_SELF_CHECK_CHANNEL_CHANGES") != "1":
        return

    planned_packages = [
        {"name": record.name, "channel": str(record.channel)} for record in link_precs
    ]
    changes = find_channel_changes(unlink_precs, planned_packages)
    if not changes:
        return

    print(
        "Warning: this update would move the following packages "
        "to a different channel:",
        file=sys.stderr,
    )
    for change in changes:
        print(
            f"  {change.name}: {change.installed_channel} -> {change.planned_channel}",
            file=sys.stderr,
        )

    # The update was explicitly opted in: warn, but do not ask or refuse.
    if os.environ.get("CONDA_SELF_ALLOW_CHANNEL_CHANGES") == "1":
        return

    from conda.base.context import context

    if context.dry_run:
        return
    if context.json or context.always_yes or not sys.stdin.isatty():
        raise CondaValueError(
            "Refusing to move packages to a different channel in "
            "non-interactive mode. Pass --allow-channel-changes to proceed."
        )

    from conda.reporters import confirm_yn

    confirm_yn(
        "Proceed with changing package channels?[y/n]:\n",
        default="no",
        dry_run=context.dry_run,
    )