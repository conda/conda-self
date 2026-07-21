from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

HELP = "Uninstall this conda installation through its installer or package manager."


def configure_parser(parser: argparse.ArgumentParser) -> None:
    from conda.cli.helpers import add_output_and_prompt_options

    parser.description = HELP
    add_output_and_prompt_options(parser)
    parser.set_defaults(func=execute)


def execute(args: argparse.Namespace) -> int:
    from pathlib import Path

    from conda.base.context import context

    from ..exceptions import InstallerOperationUnsupportedError
    from ..models import UninstallRequest
    from ..registry import get_adapter

    prefix = Path(context.root_prefix)
    adapter = get_adapter(prefix)
    if adapter is None or adapter.uninstall is None:
        raise InstallerOperationUnsupportedError("uninstall", prefix)

    return adapter.uninstall(
        UninstallRequest(
            prefix=prefix,
            dry_run=context.dry_run or bool(args.dry_run),
            yes=context.always_yes or bool(args.yes),
            json=context.json or bool(args.json),
            quiet=context.quiet or bool(args.quiet),
        )
    )
