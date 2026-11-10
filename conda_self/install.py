from __future__ import annotations

import os
import sys
from subprocess import run

from conda.base.context import context


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
    *,
    check_channel_changes: bool = False,
    allow_channel_changes: bool = False,
) -> int:
    """Install or update specs into the protected base env via subprocess."""
    env = None
    if check_channel_changes:
        env = {
            **os.environ,
            "CONDA_SELF_CHECK_CHANNEL_CHANGES": "1",
            **(
                {"CONDA_SELF_ALLOW_CHANNEL_CHANGES": "1"}
                if allow_channel_changes
                else {}
            ),
        }
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
    return run(command, env=env).returncode

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

