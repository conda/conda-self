"""Health check: Base environment protection.

Checks if the base environment is protected (frozen) and offers to
protect it by cloning to a default environment and resetting base.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from conda.base.constants import OK_MARK, PREFIX_FROZEN_FILE, X_MARK
from conda.core.prefix_data import PrefixData

if TYPE_CHECKING:
    from argparse import Namespace

    from conda.models.records import PrefixRecord
    from conda.plugins.types import ConfirmCallback

    from ..migration import MigrationPlan


BASE_PROTECTION_FROZEN_MESSAGE = """\
Your base environment is protected from direct modifications.

To install a plugin with conda 26.11 or later, run
  conda plugins install -n base PACKAGE

For other base maintenance commands, run
  conda self --help"""


def check(prefix: str, _verbose: bool) -> None:
    """Health check: Verify base environment protection status.

    Only runs when checking the base environment.
    """
    if prefix != sys.prefix:
        print("Skipping base protection: not running on the base environment.\n")
        return

    if PrefixData(prefix).is_frozen():
        print(f"{OK_MARK} Base environment is marked as frozen.\n")
    else:
        print(f"{X_MARK} Base environment is not marked as frozen.\n")
        print("Run 'conda doctor -n base base-protection --fix' to protect it.\n")


def _default_destination() -> Path:
    """Choose a destination without creating or touching environment directories."""
    import os

    from conda.base.context import context, locate_prefix_by_name
    from conda.exceptions import EnvironmentNameNotFound, NoWritableEnvsDirError

    from ..constants import DEFAULT_ENV_NAME

    try:
        return Path(locate_prefix_by_name(DEFAULT_ENV_NAME))
    except EnvironmentNameNotFound:
        for directory in context.envs_dirs:
            if directory == os.devnull:
                continue
            parent = Path(directory)
            while not parent.exists() and parent != parent.parent:
                parent = parent.parent
            if parent.is_dir() and os.access(parent, os.W_OK | os.X_OK):
                return Path(directory, DEFAULT_ENV_NAME)
    raise NoWritableEnvsDirError(context.envs_dirs)


def _untracked_manifest(prefix: Path, destination: Path) -> dict[str, tuple[str, str]]:
    """Record the exact untracked contents expected after clone prefix rewriting."""
    import hashlib

    from conda.exceptions import CondaOSError
    from conda.misc import untracked

    manifest = {}
    for filename in untracked(str(prefix)):
        path = prefix / filename
        try:
            if path.is_symlink():
                manifest[filename] = ("symlink", str(path.readlink()))
                continue
            if not path.is_file():
                raise OSError("Not a regular file")
            content = path.read_bytes()
            try:
                content = (
                    content.decode("utf-8")
                    .replace(str(prefix), str(destination))
                    .encode("utf-8")
                )
            except UnicodeDecodeError:
                pass
            manifest[filename] = ("file", hashlib.sha256(content).hexdigest())
        except OSError as error:
            raise CondaOSError(
                f"Cannot prepare untracked file {filename}: {error}"
            ) from error
    return manifest


def _verify_untracked(prefix: Path, manifest: dict[str, tuple[str, str]]) -> None:
    from conda.exceptions import CondaValueError, PathNotFoundError
    from conda.gateways.disk.read import compute_sum

    for filename, (kind, expected) in manifest.items():
        path = prefix / filename
        try:
            actual = (
                str(path.readlink())
                if kind == "symlink"
                else compute_sum(path, "sha256")
            )
            matches = actual == expected and path.is_symlink() == (kind == "symlink")
        except (OSError, PathNotFoundError):
            matches = False
        if not matches:
            raise CondaValueError(
                f"Untracked files do not match the migration plan: {filename}. "
                "Base was not changed."
            )


def _invalidate_prefix(prefix: Path) -> None:
    """Discard cached views of exactly this prefix."""
    for key in tuple(PrefixData._cache_):
        cached_path = key[0] if isinstance(key, tuple) else key
        if Path(cached_path) == prefix:
            del PrefixData._cache_[key]


def _prepare_default(
    prefix: Path, source: dict[str, PrefixRecord], plan: MigrationPlan
) -> None:
    """Trim a clone and verify its exact package set before touching base."""
    from conda.core.link import PrefixSetup, UnlinkLinkTransaction
    from conda.core.solve import diff_for_unlink_link_precs
    from conda.exceptions import CondaValueError
    from conda.history import History
    from conda.models.match_spec import MatchSpec

    _invalidate_prefix(prefix)
    installed = {
        record.name: record
        for record in PrefixData(prefix, interoperability=False).iter_records()
    }
    if installed != source:
        raise CondaValueError(
            "Cloned packages do not match the migration plan. Base was not changed."
        )

    retained = tuple(installed[name] for name in sorted(plan.default_names))
    unlink, link = diff_for_unlink_link_precs(
        str(prefix), retained, force_reinstall=False
    )
    if link:
        raise CondaValueError(
            "Preparing default would change installed packages. Base was not changed."
        )
    if unlink:
        transaction = UnlinkLinkTransaction(
            PrefixSetup(
                target_prefix=str(prefix),
                unlink_precs=unlink,
                link_precs=(),
                remove_specs=tuple(MatchSpec(record.name) for record in unlink),
                update_specs=(),
                neutered_specs=(),
            )
        )
        transaction.execute()

    _invalidate_prefix(prefix)
    actual = {
        record.name: record
        for record in PrefixData(prefix, interoperability=False).iter_records()
    }
    if actual != {name: source[name] for name in plan.default_names}:
        raise CondaValueError(
            "Default packages do not match the migration plan. Base was not changed."
        )

    # Explicit cloning records every dependency as a requested package.
    history = History(str(prefix))
    cloned_requests = history.get_requested_specs_map()
    history.update()
    history.write_specs(
        remove_specs=tuple(cloned_requests.values()), update_specs=plan.requested_specs
    )


def _print_plan(
    records: dict[str, PrefixRecord],
    plan: MigrationPlan,
    destination: Path,
    existing_destination: bool,
    external_packages: tuple[str, ...],
) -> None:
    print("Migration plan:")
    print("Versions and builds will not change. No dependency solve will run.")
    groups = (
        ("Retained in base", plan.base_names),
        ("Installed in default", plan.default_names),
        ("Excluded from default", records.keys() - plan.default_names),
        (
            "Unavailable in default (user packages requiring conda or its plugins)",
            plan.default_excluded_user_names,
        ),
        ("Removed from both environments", plan.removed_from_both_names),
    )
    for title, names in groups:
        print(f"\n{title}:")
        if not names:
            print("  (none)")
        for name in sorted(names):
            record = records[name]
            print(f"  {name} {record.version} {record.build}")
    if external_packages:
        print("\nExternal packages and untracked Python files copied to default:")
        for package in external_packages:
            print(f"  {package}")
        print("  Existing libraries are retained in default for external packages.")
        print(
            "  External files remain in base, but may no longer work after its reset."
        )
    print(f"\nDefault environment: {destination}")
    if existing_destination:
        print(
            "  The existing destination will be removed and recreated "
            "after confirmation."
        )
    print("Base will be marked as frozen.")
    print(f"Default activation will change to: {destination}\n")


def fix(prefix: str, args: Namespace, confirm: ConfirmCallback) -> int:
    """Preview and apply an exact-version separation of base and default."""
    import io
    import json
    from contextlib import nullcontext, redirect_stdout

    from conda.base.context import context
    from conda.cli.condarc import ConfigurationFile
    from conda.exceptions import CondaOSError, CondaValueError, DryRunExit
    from conda.gateways.disk.delete import rm_rf
    from conda.history import History
    from conda.misc import clone_env
    from conda.models.environment import Environment

    from ..constants import (
        DEFAULT_ENV_NAME,
        RESET_FILE_BASE_PROTECTION,
        RESET_FILE_INSTALLER,
        SELF_PERMANENT_PACKAGES_SETTING,
    )
    from ..migration import plan_migration
    from ..migration_inventory import inspect_migration_inventory
    from ..reset import names_from_explicit, reset, verify_installed_records

    if prefix != sys.prefix:
        print("Skipping: not running on the base environment.")
        return 0
    if PrefixData(prefix).is_frozen():
        print("Base environment is already protected.")
        return 0

    with context._override("prefix_data_interoperability", False):
        base_prefix = Path(prefix)
        records = {
            record.name: record
            for record in PrefixData(base_prefix, interoperability=False)
            .reload()
            .iter_records()
        }
        inventory = inspect_migration_inventory(base_prefix, records.values())
        requested = History(prefix).get_requested_specs_map()
        base_roots: set[str] = set(
            getattr(context.plugins, SELF_PERMANENT_PACKAGES_SETTING, ())
        )
        installer_snapshot = base_prefix / "conda-meta" / RESET_FILE_INSTALLER
        if installer_snapshot.exists():
            base_roots.update(names_from_explicit(installer_snapshot))
        plan = plan_migration(
            records.values(),
            plugin_names=inventory.plugin_names,
            requested_specs=requested,
            base_roots=base_roots,
            virtual_records=context.plugin_manager.get_virtual_package_records(),
            preserve_dependencies=bool(inventory.external_packages),
        )
        missing_external_requirements = (
            inventory.external_required_names - plan.default_names
        )
        if missing_external_requirements:
            raise CondaValueError(
                "External packages require packages excluded from default: "
                + ", ".join(sorted(missing_external_requirements))
                + ". Resolve these dependencies before migrating. "
                "No environments were changed."
            )

        destination = _default_destination()
        destination_data = PrefixData(destination, interoperability=False)
        if base_prefix.resolve().is_relative_to(destination.resolve()):
            raise CondaValueError(
                "The default destination must not contain the base environment."
            )
        existing_environment = destination_data.is_environment()
        existing_destination = destination_data.exists() or destination.is_symlink()
        snapshot_file = base_prefix / "conda-meta" / RESET_FILE_BASE_PROTECTION
        if snapshot_file.exists() and existing_destination:
            if names_from_explicit(snapshot_file) - records.keys():
                raise CondaValueError(
                    "An earlier migration may have already reset base. The existing "
                    "default environment and recovery snapshot have been preserved. "
                    "Restore base with 'conda self reset --snapshot base-protection' "
                    "before retrying protection."
                )
        env = Environment(
            name="base",
            prefix=prefix,
            platform=context.subdir,
            explicit_packages=list(records.values()),
        )
        try:
            exporter = context.plugin_manager.get_environment_exporter_by_format(
                "explicit"
            )
            export = exporter.export
            assert export is not None
            snapshot_content = export(env)
        except CondaValueError as error:
            raise CondaValueError(
                "Cannot prepare the recovery snapshot. No environments were changed."
            ) from error
        untracked_manifest = _untracked_manifest(base_prefix, destination)
        _print_plan(
            records,
            plan,
            destination,
            existing_destination,
            inventory.external_packages,
        )
        confirm("Proceed?")
        # Also protect direct fixer callers whose callback does not implement dry-run.
        if context.dry_run:
            raise DryRunExit()
        if existing_destination:
            confirm(
                f"Environment '{DEFAULT_ENV_NAME}' already exists. Remove and recreate?"
                if existing_environment
                else f"Directory exists at '{destination}'. Remove and recreate?"
            )

        verify_installed_records(base_prefix, records.values())
        if _untracked_manifest(base_prefix, destination) != untracked_manifest:
            raise CondaValueError(
                "Base files changed after migration planning. "
                "Review a new plan before proceeding."
            )
        snapshot_file.write_text(snapshot_content)

        if existing_destination:
            rm_rf(destination)
            if destination.exists():
                raise CondaOSError("Could not remove the existing default destination.")
        _invalidate_prefix(destination)
        stdout_ctx = redirect_stdout(io.StringIO()) if context.quiet else nullcontext()
        with stdout_ctx:
            clone_env(prefix, str(destination), verbose=False, quiet=True)
            _prepare_default(destination, records, plan)
            _verify_untracked(destination, untracked_manifest)
            verify_installed_records(base_prefix, records.values())
            if _untracked_manifest(base_prefix, destination) != untracked_manifest:
                raise CondaValueError(
                    "Base files changed during migration. Base was not reset."
                )
            try:
                reset(
                    prefix=prefix,
                    uninstallable_packages=set(plan.base_names),
                    expected_records=tuple(records.values()),
                )
            finally:
                _invalidate_prefix(base_prefix)

    try:
        (base_prefix / PREFIX_FROZEN_FILE).write_text(
            json.dumps({"message": BASE_PROTECTION_FROZEN_MESSAGE})
        )
    except OSError as error:
        raise CondaOSError(
            f"Could not protect the base environment: {error}. "
            "Base was reset and default is ready. The recovery snapshot "
            "has been preserved. Restore base with "
            "'conda self reset --snapshot base-protection' before retrying."
        ) from error
    try:
        with ConfigurationFile.from_user_condarc() as config:
            config.set_key("default_activation_env", str(destination))
    except OSError as error:
        raise CondaOSError(
            "Base is protected and default is ready, but activation configuration "
            "could not be updated. Run "
            "'conda config --set default_activation_env default' "
            "to finish, or run 'conda activate default' to use it now."
        ) from error
    if not context.quiet:
        print(f"\nDone! To use your packages: conda activate {DEFAULT_ENV_NAME}")
    return 0
