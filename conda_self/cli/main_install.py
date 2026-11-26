from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

REPLACEMENT = "Use conda plugins install -n base with conda 26.11 or later."
HELP = f"Install conda plugins in base (pending deprecation). {REPLACEMENT}"


def configure_parser(parser: argparse.ArgumentParser) -> None:
    from conda.cli.helpers import add_output_and_prompt_options

    parser.description = HELP
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

    from ..install import install_specs_in_protected_env

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

    return install_specs_in_protected_env(
        args.specs,
        plugins_only=True,
        force_reinstall=args.force_reinstall,
        dry_run=context.dry_run,
        json=context.json,
        yes=context.always_yes,
        quiet=context.quiet,
        console=args.console,
        verbosity=context.verbosity,
    )
