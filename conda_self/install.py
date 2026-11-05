from __future__ import annotations
import sys
from subprocess import run
from json import loads
from typing import Any

from conda.base.context import context
from conda.exceptions import CondaError

# def install_specs_in_protected_env(
#     specs: list[str],
#     force_reinstall: bool = False,
#     update_dependencies: bool = False,
#     update_all: bool = False,
#     dry_run: bool = False,
#     json: bool = False,
#     yes: bool = False,
#     quiet: bool = False,
# ) -> int:
#     """Install or update specs into the protected base env via subprocess."""
#     if update_all:
#         update_flag = "--all"
#     elif update_dependencies:
#         update_flag = "--update-deps"
#     else:
#         update_flag = "--update-specs"
#     process = run(
#         [
#             sys.executable,
#             "-m",
#             "conda",
#             "install",
#             f"--prefix={sys.prefix}",
#             *(
#                 ("--override-frozen",)
#                 if hasattr(context, "protect_frozen_envs")
#                 else ()
#             ),
#             *(("--force-reinstall",) if force_reinstall else ()),
#             *(("--dry-run",) if dry_run else ()),
#             *(("--json",) if json else ()),
#             *(("--yes",) if yes else ()),
#             *(("--quiet",) if quiet else ()),
#             update_flag,
#             *specs,
#         ]
#     )
#     return process.returncode


def install_command_to_run(
    specs: list[str],
    *,
    force_reinstall: bool = False,
    update_dependencies: bool = False,
    update_all: bool = False,
    dry_run: bool = False,
    json: bool = False,
    yes: bool = False,
    quiet: bool = False,
) -> list[str]:
    """Build the full `conda install` command (with correct flags) for the protected base env."""
    if update_all:
        update_flag = "--all"
    elif update_dependencies:
        update_flag = "--update-deps"
    else:
        update_flag = "--update-specs"
    return [
        sys.executable, "-m", "conda", "install",
        f"--prefix={sys.prefix}",
        *(("--override-frozen",) if hasattr(context, "protect_frozen_envs") else ()),
        *(("--force-reinstall",) if force_reinstall else ()),
        *(("--dry-run",) if dry_run else ()),
        *(("--json",) if json else ()),
        *(("--yes",) if yes else ()),
        *(("--quiet",) if quiet else ()),
        update_flag,
        *specs,
    ]

def install_specs_in_protected_env(
    specs: list[str],
    force_reinstall: bool = False,
    update_dependencies: bool = False,
    update_all: bool = False,
    dry_run: bool = False,
    json: bool = False,
    yes: bool = False,
    quiet: bool = False,
) -> int:
    """Install or update specs into the protected base env via subprocess."""
    command = install_command_to_run(
        specs,
        force_reinstall=force_reinstall,
        update_dependencies=update_dependencies,
        update_all=update_all,
        dry_run=dry_run,
        json=json,
        yes=yes,
        quiet=quiet,
    )
    return run(command).returncode

def uninstall_specs_in_protected_env(
    specs: list[str],
    json: bool = False,
    yes: bool = True,
) -> int:
    cmd = [
        sys.executable,
        "-m",
        "conda",
        "remove",
        f"--prefix={sys.prefix}",
        *(("--override-frozen",) if hasattr(context, "protect_frozen_envs") else ()),
        *(("--json",) if json else ()),
        *(("--yes",) if yes else ()),
        *specs,
    ]
    process = run(cmd)
    return process.returncode

def planned_packages(
    specs: list[str],
    *,
    force_reinstall: bool = False,
    update_dependencies: bool = False,
    update_all: bool = False,
) -> list[dict[str, Any]]:
    """Solve an install without applying it; return the planned packages."""
    command = install_command_to_run(
        specs,
        force_reinstall=force_reinstall,
        update_dependencies=update_dependencies,
        update_all=update_all,
        dry_run=True,   # forced: solve only, apply nothing
        json=True,      # forced: machine-readable plan on stdout
        yes=True,       # captured subprocess has no terminal to prompt on)
    )

    result = run(command, capture_output=True, text=True)
    plan = loads(result.stdout)
    if result.returncode != 0 or not plan.get("success", False):
        raise CondaError(
            plan.get("message") or result.stderr or "Could not compute the update plan."
        )
    return plan["actions"]["LINK"]

