from __future__ import annotations

import sys
from importlib.util import find_spec
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

REPLACEMENT = "Use conda plugins install --name base with conda 26.11 or later."
HELP = f"Install conda plugins in base (pending deprecation). {REPLACEMENT}"


def configure_parser(parser: argparse.ArgumentParser) -> None:
    from conda.cli.helpers import add_output_and_prompt_options

    parser.description = HELP
    parser.epilog = (
        "For a protected base environment, add --override-frozen "
        "to conda plugins install."
    )
    add_output_and_prompt_options(parser)
    parser.add_argument(
        "--force-reinstall",
        action="store_true",
        help="Reinstall each requested package even if it is already installed.",
    )
    parser.add_argument("specs", nargs="+", help="Conda plugins to install")
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    import warnings

    from conda.base.context import context
    from conda.exceptions import CondaValueError
    from conda.models.match_spec import MatchSpec

    from ..install import run_in_protected_env

    warnings.warn(
        f"conda self install is pending deprecation. {REPLACEMENT}",
        PendingDeprecationWarning,
        stacklevel=2,
    )
    specs_to_add = [MatchSpec(spec) for spec in args.specs]

    specs_with_channels = [str(s) for s in specs_to_add if s.get("channel")]
    if specs_with_channels:
        joined = ", ".join(specs_with_channels)
        raise CondaValueError(
            f"Channel-qualified package specs are not supported: {joined}\n"
            "Configure channels via `conda config --add channels <channel>` instead."
        )

    if not context.json and not context.quiet:
        print("Installing packages:", *args.specs, flush=True)

    options = ["--update-specs"]
    if args.force_reinstall:
        options.append("--force-reinstall")
    if args.console:
        options.extend(("--console", args.console))
    options.extend(["--verbose"] * context.verbosity)

    # Older conda versions may lack the parent package or only provide list and info.
    plugins_package = "conda.plugins.subcommands.plugins"
    native_install = find_spec(plugins_package) and find_spec(
        f"{plugins_package}.install"
    )
    # Hold legacy install output until we know which JSON result to report.
    validate_after_install = not native_install and not context.dry_run
    result = run_in_protected_env(
        ("plugins", "install") if native_install else ("install",),
        [*options, "--", *args.specs],
        dry_run=context.dry_run,
        json=context.json,
        yes=context.always_yes,
        quiet=context.quiet,
        capture_stdout=context.json and validate_after_install,
    )
    if result.returncode == 0 and validate_after_install:
        from ..exceptions import NotAPluginError
        from ..validate import (
            conda_plugin_packages,
            normalize_plugin_name,
            reload_plugin_packages,
        )

        reload_plugin_packages()
        plugin_names = conda_plugin_packages()
        invalid_names = [
            spec.name
            for spec in specs_to_add
            if normalize_plugin_name(spec.name) not in plugin_names
        ]
        if invalid_names:
            cleanup = run_in_protected_env(
                ("remove",), invalid_names, yes=True, capture_stdout=context.json
            )
            if cleanup.returncode and cleanup.stdout:
                sys.stderr.write(cleanup.stdout)
            raise NotAPluginError(invalid_names)

    if result.stdout is not None:
        sys.stdout.write(result.stdout)
    return result.returncode
