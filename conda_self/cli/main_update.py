from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

HELP = "Update conda and all installed conda plugins by default."


def configure_parser(parser: argparse.ArgumentParser) -> None:
    from conda.cli.helpers import add_output_and_prompt_options

    parser.description = HELP
    add_output_and_prompt_options(parser)
    parser.add_argument(
        "--force-reinstall",
        action="store_true",
        help=(
            "Uninstall and reinstall each requested package, even if it is "
            "already installed."
        ),
    )
    update_group = parser.add_mutually_exclusive_group()
    update_group.add_argument(
        "--plugin",
        help="Name of a conda plugin to update",
    )
    update_group.add_argument(
        "--all",
        action="store_true",
        help="Update conda and all installed conda plugins (default).",
    )
    update_group.add_argument(
        "--conda-only",
        action="store_true",
        help="Update conda and its dependencies without targeting all conda plugins.",
    )
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    from conda.base.context import context
    from conda.core.prefix_data import PrefixData
    from conda.exceptions import PackageNotInstalledError

    from ..install import install_specs_in_protected_env
    from ..validate import conda_plugin_packages, validate_plugin_is_installed

    if args.plugin:
        validate_plugin_is_installed(args.plugin)
        package_names = [args.plugin]
    elif args.conda_only:
        package_names = ["conda"]
    else:
        package_names = ["conda", *conda_plugin_packages()]

    prefix_data = PrefixData(context.root_prefix)

    specs = []
    info_parts = []
    for name in package_names:
        installed = prefix_data.get(name)
        if not installed:
            raise PackageNotInstalledError(context.root_prefix, name)
        specs.append(f"{name}>={installed.version}")
        info_parts.append(f"{name} (installed: {installed.version})")

    quiet = context.quiet or bool(args.quiet)
    if not context.json and not quiet:
        print(f"Updating {', '.join(info_parts)}...")

    return install_specs_in_protected_env(
        specs=specs,
        force_reinstall=args.force_reinstall,
        update_dependencies=True,
        dry_run=context.dry_run,
        json=context.json,
        yes=context.always_yes,
        quiet=quiet,
    )
