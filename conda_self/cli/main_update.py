from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

HELP = "Update 'conda' and/or its plugins in the 'base' environment."


def configure_parser(parser: argparse.ArgumentParser) -> None:
    from conda.cli.helpers import add_output_and_prompt_options

    parser.description = HELP
    add_output_and_prompt_options(parser)
    parser.add_argument(
        "--force-reinstall",
        action="store_true",
        help="Install latest conda available even "
        "if currently installed is more recent.",
    )
    update_group = parser.add_mutually_exclusive_group()
    update_group.add_argument(
        "--plugin",
        help="Name of a conda plugin to update",
    )
    update_group.add_argument(
        "--all",
        action="store_true",
        help="Update conda, all plugins, and dependencies.",
    )
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    from pathlib import Path

    from conda.base.context import context
    from conda.core.prefix_data import PrefixData
    from conda.exceptions import PackageNotInstalledError

    from ..install import install_specs_in_protected_env
    from ..models import LauncherUpdateRequest
    from ..registry import get_adapter
    from ..validate import conda_plugin_packages, validate_plugin_is_installed

    if args.plugin:
        validate_plugin_is_installed(args.plugin)
        package_names = [args.plugin]
    elif args.all:
        package_names = ["conda", *conda_plugin_packages()]
    else:
        prefix = Path(context.root_prefix)
        adapter = get_adapter(prefix)
        if adapter is not None and adapter.update_launcher is not None:
            return adapter.update_launcher(
                LauncherUpdateRequest(
                    prefix=prefix,
                    force_reinstall=args.force_reinstall,
                    dry_run=context.dry_run or bool(args.dry_run),
                    yes=context.always_yes or bool(args.yes),
                    json=context.json or bool(args.json),
                    quiet=context.quiet or bool(args.quiet),
                )
            )
        package_names = ["conda"]

    prefix_data = PrefixData(context.root_prefix)

    info_parts = []
    for name in package_names:
        installed = prefix_data.get(name)
        if not installed:
            raise PackageNotInstalledError(context.root_prefix, name)
        info_parts.append(f"{name} (installed: {installed.version})")

    if not context.quiet:
        print(f"Updating {', '.join(info_parts)}...")

    return install_specs_in_protected_env(
        specs=package_names,
        force_reinstall=args.force_reinstall,
        update_dependencies=args.all,
        dry_run=context.dry_run,
        json=context.json,
        yes=context.always_yes,
    )
