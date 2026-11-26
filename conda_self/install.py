import sys
from subprocess import run


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
    plugins_only: bool = False,
    console: str | None = None,
    verbosity: int = 0,
) -> int:
    """Install or update specs in the running conda installation."""
    if update_all:
        update_flag = "--all"
    elif update_dependencies:
        update_flag = "--update-deps"
    else:
        update_flag = "--update-specs"

    if plugins_only:
        install_command = ["plugins", "install", "-n", "base"]
    else:
        install_command = ["install", f"--prefix={sys.prefix}", "--override-frozen"]

    cmd = [
        sys.executable,
        "-m",
        "conda",
        *install_command,
        *(("--force-reinstall",) if force_reinstall else ()),
        *(("--dry-run",) if dry_run else ()),
        *(("--json",) if json else ()),
        *(("--yes",) if yes else ()),
        *(("--quiet",) if quiet else ()),
        *(("--console", console) if console else ()),
        *(["--verbose"] * verbosity),
        update_flag,
        *(("--",) if plugins_only else ()),
        *specs,
    ]
    return run(cmd).returncode
