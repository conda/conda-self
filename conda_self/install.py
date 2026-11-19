import sys
from importlib.util import find_spec
from subprocess import PIPE, run

from conda.base.context import context


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

    # Older conda versions may lack the parent package or only provide list and info.
    plugins = "conda.plugins.subcommands.plugins"
    native_install = (
        plugins_only and find_spec(plugins) and find_spec(f"{plugins}.install")
    )
    validate_after_install = plugins_only and not native_install and not dry_run
    cmd = [
        sys.executable,
        "-m",
        "conda",
        *(("plugins",) if native_install else ()),
        "install",
        f"--prefix={sys.prefix}",
        *(("--override-frozen",) if hasattr(context, "protect_frozen_envs") else ()),
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
    # Hold legacy install JSON until validation and any rollback finish.
    result = run(
        cmd, stdout=PIPE if json and validate_after_install else None, text=True
    )
    if result.returncode == 0 and validate_after_install:
        from conda.models.match_spec import MatchSpec

        from .exceptions import NotAPluginError
        from .validate import (
            conda_plugin_packages,
            normalize_plugin_name,
            reload_plugin_packages,
        )

        reload_plugin_packages()
        plugin_names = conda_plugin_packages()
        invalid_names = [
            spec.name
            for spec in map(MatchSpec, specs)
            if normalize_plugin_name(spec.name) not in plugin_names
        ]
        if invalid_names:
            uninstall_specs_in_protected_env(invalid_names, quiet_on_success=json)
            raise NotAPluginError(invalid_names)

    if result.stdout is not None:
        sys.stdout.write(result.stdout)
    return result.returncode


def uninstall_specs_in_protected_env(
    specs: list[str],
    json: bool = False,
    yes: bool = True,
    *,
    quiet_on_success: bool = False,
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
    result = run(cmd, stdout=PIPE if quiet_on_success else None, text=True)
    if result.returncode and result.stdout:
        sys.stderr.write(result.stdout)
    return result.returncode
