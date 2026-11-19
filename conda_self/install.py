import sys
from subprocess import PIPE, CompletedProcess, run

from conda.base.context import context


def run_in_protected_env(
    command: tuple[str, ...],
    args: list[str],
    *,
    dry_run: bool = False,
    json: bool = False,
    yes: bool = False,
    quiet: bool = False,
    capture_stdout: bool = False,
) -> CompletedProcess[str]:
    """Run conda against its own prefix, including when base is frozen."""
    cmd = [
        sys.executable,
        "-m",
        "conda",
        *command,
        f"--prefix={sys.prefix}",
        *(("--override-frozen",) if hasattr(context, "protect_frozen_envs") else ()),
        *(("--dry-run",) if dry_run else ()),
        *(("--json",) if json else ()),
        *(("--yes",) if yes else ()),
        *(("--quiet",) if quiet else ()),
        *args,
    ]
    return run(cmd, stdout=PIPE if capture_stdout else None, text=True)


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
    if update_all:
        update_flag = "--all"
    elif update_dependencies:
        update_flag = "--update-deps"
    else:
        update_flag = "--update-specs"
    return run_in_protected_env(
        ("install",),
        [*(("--force-reinstall",) if force_reinstall else ()), update_flag, *specs],
        dry_run=dry_run,
        json=json,
        yes=yes,
        quiet=quiet,
    ).returncode


def uninstall_specs_in_protected_env(
    specs: list[str],
    json: bool = False,
    yes: bool = True,
) -> int:
    return run_in_protected_env(("remove",), specs, json=json, yes=yes).returncode
