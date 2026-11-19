from __future__ import annotations

import json
import sys
from subprocess import CompletedProcess
from typing import TYPE_CHECKING

import pytest
from conda.base.constants import PREFIX_FROZEN_FILE
from conda.exceptions import CondaValueError

from conda_self.testing import conda_cli_subprocess, is_installed

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture
    from pytest import MonkeyPatch


def test_help(conda_cli: CondaCLIFixture):
    out, err, exc = conda_cli("self", "install", "--help", raises=SystemExit)
    assert exc.value.code == 0
    help_text = " ".join(out.split())
    assert "pending deprecation" in help_text.lower()
    assert "conda plugins install --name base" in help_text


def test_install_plugin_dry_run(
    monkeypatch: MonkeyPatch,
    conda_channel: str,
):
    monkeypatch.setenv("CONDA_CHANNELS", conda_channel)
    result = conda_cli_subprocess(
        sys.prefix,
        "self",
        "install",
        "--json",
        "--dry-run",
        "conda-libmamba-solver",
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout)["success"]


@pytest.mark.parametrize("native", (False, True), ids=("legacy", "native"))
def test_install_forwards_options(
    native: bool,
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        "conda_self.cli.main_install._has_native_plugins_install", lambda: native
    )
    monkeypatch.setenv("CONDA_PREFIX", str(tmp_path))
    commands: list[list[str]] = []

    def run(command: list[str], **kwargs) -> CompletedProcess[str]:
        commands.append(command)
        print('{"success": true}')
        return CompletedProcess(command, 0)

    monkeypatch.setattr("conda_self.install.run", run)
    specs = ["conda-build>=26", "conda-pack"]
    with pytest.warns(
        PendingDeprecationWarning, match="conda plugins install --name base"
    ):
        out, _, code = conda_cli(
            "self",
            "install",
            "--force-reinstall",
            "-y",
            "-q",
            "-d",
            "-vv",
            "--console",
            "classic",
            "--json",
            *specs,
        )

    assert code == 0
    assert json.loads(out) == {"success": True}
    (command,) = commands
    subcommand = ["plugins", "install"] if native else ["install"]
    assert command[: 3 + len(subcommand)] == [
        sys.executable,
        "-m",
        "conda",
        *subcommand,
    ]
    assert command[-len(specs) :] == specs
    assert command[command.index("--console") + 1] == "classic"
    assert command.count("--verbose") == 2
    for flag in (
        f"--prefix={sys.prefix}",
        "--override-frozen",
        "--update-specs",
        "--force-reinstall",
        "--yes",
        "--quiet",
        "--dry-run",
        "--json",
    ):
        assert flag in command


@pytest.mark.parametrize("returncode", (0, 17))
def test_native_install_preserves_prompt_and_exit_code(
    returncode: int,
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
):
    monkeypatch.setattr(
        "conda_self.cli.main_install._has_native_plugins_install", lambda: True
    )
    monkeypatch.setenv("CONDA_ALWAYS_YES", "false")
    commands: list[list[str]] = []

    def run(command: list[str], **kwargs) -> CompletedProcess[str]:
        commands.append(command)
        return CompletedProcess(command, returncode)

    monkeypatch.setattr("conda_self.install.run", run)
    _, _, code = conda_cli("self", "install", "example-plugin")

    assert code == returncode
    (command,) = commands
    assert command[3:5] == ["plugins", "install"]
    assert "--yes" not in command


@pytest.mark.parametrize(
    "spec",
    (
        pytest.param("conda-fake-solver", id="dry-run-not-found"),
        pytest.param("idontexist", id="not-found"),
    ),
)
def test_install_not_found(conda_cli: CondaCLIFixture, spec: str):
    _, _, code = conda_cli("self", "install", spec)
    assert code != 0


@pytest.mark.parametrize(
    ("package_names", "options"),
    (
        pytest.param(("flask",), (), id="single-package"),
        pytest.param(("flask", "numpy"), ("--json",), id="multiple-packages-json"),
    ),
)
def test_install_not_plugins(
    package_names: tuple[str, ...],
    options: tuple[str, ...],
    monkeypatch: MonkeyPatch,
    base_env: Path,
    conda_channel: str,
):
    monkeypatch.setenv("CONDA_CHANNELS", conda_channel)

    history = base_env / "conda-meta" / "history"
    before_install = history.read_bytes()
    native_help = conda_cli_subprocess(
        base_env,
        "plugins",
        "install",
        "--help",
        check=False,
        capture_output=True,
    )

    result = conda_cli_subprocess(
        base_env,
        "self",
        "install",
        "--yes",
        *options,
        *package_names,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    error = json.loads(result.stdout)["error"] if "--json" in options else result.stderr
    if native_help.returncode == 0:
        assert "Not conda plugin packages" in error
        assert history.read_bytes() == before_install
    else:
        assert "NotAPluginError" in error
    for package_name in package_names:
        assert package_name in error
        assert not is_installed(base_env, package_name)


@pytest.mark.parametrize(
    "spec",
    (
        "conda-forge::conda-libmamba-solver",
        "defaults::conda-libmamba-solver",
    ),
)
def test_install_channel_in_spec_rejected(conda_cli: CondaCLIFixture, spec: str):
    conda_cli("self", "install", spec, raises=CondaValueError)


def test_install_plugin(
    monkeypatch: MonkeyPatch,
    base_env: Path,
    conda_channel: str,
):
    monkeypatch.setenv("CONDA_CHANNELS", conda_channel)
    (base_env / PREFIX_FROZEN_FILE).touch()

    assert not is_installed(base_env, "conda-build")
    conda_cli_subprocess(
        base_env,
        "self",
        "install",
        "--yes",
        "conda-build",
    )
    assert is_installed(base_env, "conda-build")
