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

    from conda.models.records import PackageRecord


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
    # 'defaults' expands to pkgs/main, pkgs/r, ... — treat that family as one
    # channel *per host*, so a mirror move still counts as a change.
    if parsed_channel.canonical_name == "defaults":
        if parsed_channel.location:
            return f"defaults@{parsed_channel.location}"
        return "defaults"
    return parsed_channel.base_url or parsed_channel.canonical_name or raw_channel


def find_channel_changes(
    installed_records: Iterable[PackageRecord],
    planned_packages: Iterable[Mapping[str, Any]],
) -> list[ChannelChange]:
    """Return packages whose planned channel differs from the installed one.

    Packages whose channel cannot be compared (unknown on either side) are
    included too — same consent path as a real channel move.
    """
    # Map each installed package name to its channel in two forms:
    # the raw form for display, and the normalized form for comparison
    # (None when the installed channel cannot be compared).
    installed_by_name: dict[str, tuple[str, str | None]] = {}
    for record in installed_records:
        raw_channel = str(record.channel)
        installed_by_name[record.name] = (
            raw_channel,
            normalize_channel(record.channel),
        )

    changes: list[ChannelChange] = []
    for package in planned_packages:
        name = package["name"]
        if name not in installed_by_name:
            continue  # newly installed package: out of scope for the ticket
        planned_raw_channel = package.get("channel") or package.get("base_url")
        planned_normalized_channel = normalize_channel(planned_raw_channel)
        installed_raw_channel, installed_normalized_channel = installed_by_name[name]
        planned_display = (
            str(planned_raw_channel) if planned_raw_channel is not None else "<unknown>"
        )

        if (
            installed_normalized_channel is None
            or planned_normalized_channel is None
            or planned_normalized_channel != installed_normalized_channel
        ):
            changes.append(
                ChannelChange(
                    name=name,
                    installed_channel=installed_raw_channel,
                    planned_channel=planned_display,
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
                f"  {change.name}: {change.installed_channel} -> {change.planned_channel}",
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
