"""Read package metadata needed to plan a base-protection migration."""

from __future__ import annotations

from configparser import ConfigParser
from configparser import Error as ConfigParserError
from dataclasses import dataclass
from importlib.metadata import Distribution
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.context import context
from conda.common.path import get_python_site_packages_short_path
from conda.exceptions import CondaValueError
from conda.plugins.prefix_data_loaders.pypi.pkg_format import (
    get_site_packages_anchor_files,
)
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

if TYPE_CHECKING:
    from collections.abc import Iterable

    from conda.models.records import PrefixRecord


@dataclass(frozen=True)
class MigrationInventory:
    plugin_names: frozenset[str]
    external_packages: tuple[str, ...]
    external_required_names: frozenset[str]


def inspect_migration_inventory(
    prefix: Path, records: Iterable[PrefixRecord]
) -> MigrationInventory:
    """Find plugins and external Python packages without importing their code."""
    records = tuple(records)
    owners = {
        prefix / filename: record.name
        for record in records
        for filename in record.files
    }
    sites: set[Path] = set()
    for record in records:
        if record.name == "python":
            sites.add(
                prefix
                / (
                    record.python_site_packages_path
                    or get_python_site_packages_short_path(record.version)
                )
            )
    try:
        for path in owners:
            parts = path.relative_to(prefix).parts
            for index, part in enumerate(parts):
                if part == "site-packages":
                    sites.add(prefix.joinpath(*parts[: index + 1]))
                if part.endswith((".dist-info", ".egg-info")):
                    metadata = prefix.joinpath(*parts[: index + 1])
                    sites.add(metadata.parent)
                    if parts[-1] in {
                        "entry_points.txt",
                        "RECORD",
                        "METADATA",
                        "PKG-INFO",
                        "requires.txt",
                    }:
                        path.read_text(encoding="utf-8")
                    break
    except (OSError, UnicodeError):
        raise CondaValueError(
            "Recorded Python package metadata is missing or unreadable. "
            "Repair the package metadata before protecting base."
        ) from None

    tracked = set(owners)
    external: list[str] = []
    required: set[str] = set()
    names: dict[str, str] = {
        canonicalize_name(record.name): record.name for record in records
    }
    for site in sorted(sites):
        try:
            anchors = get_site_packages_anchor_files(
                site, site.relative_to(prefix).as_posix()
            )
        except FileNotFoundError:
            continue
        except OSError:
            raise CondaValueError(
                "Cannot inspect Python package metadata before protecting base."
            ) from None
        for anchor in sorted(anchors):
            if anchor.endswith(".egg-link"):
                continue
            try:
                anchor_path = prefix / anchor
                metadata = (
                    anchor_path if anchor.endswith(".egg-info") else anchor_path.parent
                )
                owner = (
                    owners.get(anchor_path)
                    or owners.get(metadata / "METADATA")
                    or owners.get(metadata / "PKG-INFO")
                    or owners.get(metadata / "entry_points.txt")
                )
                distribution = Distribution.at(metadata)
                info = distribution.metadata
                name = info["Name"] if "Name" in info else ""
                version = info["Version"] if "Version" in info else ""
                if not name or not version:
                    raise ValueError("Missing distribution name or version")
                normalized_name = canonicalize_name(name, validate=True)
                Version(version)
                points = ConfigParser(interpolation=None)
                # ConfigParser supports overriding this method on an instance.
                points.optionxform = str  # ty: ignore[invalid-assignment]
                entry_points_file = metadata / "entry_points.txt"
                has_entry_points = entry_points_file.exists()
                if has_entry_points:
                    # Conda's plugin detector skips unreadable metadata. Reject it
                    # here before deciding which installed packages can be removed.
                    points.read_string(entry_points_file.read_text(encoding="utf-8"))
                    # Entry-point sections do not inherit values from [DEFAULT].
                    points[points.default_section].clear()
                requirements = {
                    canonicalize_name(Requirement(value).name)
                    for value in distribution.requires or ()
                }
                tracked.update(
                    Path(str(distribution.locate_file(file)))
                    for file in distribution.files or ()
                )
            except (
                OSError,
                UnicodeError,
                ValueError,
                ConfigParserError,
                TypeError,
            ):
                raise CondaValueError(
                    "Cannot read complete Python package metadata. "
                    "Repair the package metadata before protecting base."
                ) from None
            if owner:
                if has_entry_points and entry_points_file not in owners:
                    raise CondaValueError(
                        "Conda package entry-point metadata is not recorded. "
                        "Repair the package metadata before protecting base."
                    )
                names[normalized_name] = owner
            else:
                if points.has_section("conda") and points["conda"]:
                    raise CondaValueError(
                        f"Cannot migrate the externally installed conda plugin {name}. "
                        "Install it as a conda package before protecting base."
                    )
                external.append(f"{name}=={version}")
                required.update(requirements)

    untracked_python = False
    try:
        for site in sites:
            for path in site.rglob("*"):
                if not path.is_file():
                    continue
                if path.suffix in {".pth", ".egg-link"} and path not in owners:
                    raise CondaValueError(
                        "Cannot safely migrate external Python import redirects. "
                        "Replace editable or path-based installations with regular "
                        "packages before protecting base."
                    )
                if (
                    path not in tracked
                    and path.suffix in {".py", ".pyi", ".pyc", ".so", ".pyd", ".egg"}
                    and "__pycache__" not in path.parts
                    and not any(
                        part.endswith((".dist-info", ".egg-info"))
                        for part in path.parts
                    )
                ):
                    untracked_python = True
    except OSError:
        raise CondaValueError(
            "Cannot inspect Python package files before protecting base."
        ) from None
    if untracked_python:
        external.append("untracked Python files")

    return MigrationInventory(
        plugin_names=frozenset(
            record.name
            for record in records
            if context.plugin_manager.is_conda_plugin_package(record, prefix=prefix)
        ),
        external_packages=tuple(sorted(external)),
        external_required_names=frozenset(
            names[name] for name in required if name in names
        ),
    )
