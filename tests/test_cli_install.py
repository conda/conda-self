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
    from pytest_mock import MockerFixture


def test_help(conda_cli: CondaCLIFixture):
    out, err, exc = conda_cli("self", "install", "--help", raises=SystemExit)
    assert exc.value.code == 0
    help_text = " ".join(out.split())
    assert "pending deprecation" in help_text.lower()
    assert "conda plugins install -n base" in help_text
    assert "--override-frozen" not in help_text


def test_install_plugin_dry_run(
    monkeypatch: MonkeyPatch,
    conda_channel: str,
):
    monkeypatch.setenv("CONDA_CHANNELS", conda_channel)
    monkeypatch.setenv("PYTHONFAULTHANDLER", "1")
    result = conda_cli_subprocess(
        sys.prefix,
        "self",
        "install",
        "--json",
        "--dry-run",
        "conda-libmamba-solver",
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert json.loads(result.stdout)["success"]


def test_install_forwards_options(
    mocker: MockerFixture,
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
):
    monkeypatch.setenv("CONDA_PREFIX", str(tmp_path))

    def report_success(command: list[str], **kwargs) -> CompletedProcess[str]:
        print('{"success": true}')
        return CompletedProcess(command, 0)

    run = mocker.patch("conda_self.install.run", side_effect=report_success)
    specs = ["conda-build>=26", "conda-pack"]
    with pytest.warns(
        PendingDeprecationWarning,
        match=r"conda plugins install -n base",
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
    run.assert_called_once()
    (command,) = run.call_args.args
    invocation = ["plugins", "install", "-n", "base"]
    assert "--override-frozen" not in command
    assert f"--prefix={sys.prefix}" not in command
    assert command[: 3 + len(invocation)] == [
        sys.executable,
        "-m",
        "conda",
        *invocation,
    ]
    assert command[-len(specs) :] == specs
    assert command[command.index("--console") + 1] == "classic"
    assert command.count("--verbose") == 2
    for flag in (
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
    mocker: MockerFixture,
):
    monkeypatch.setenv("CONDA_ALWAYS_YES", "false")
    run = mocker.patch(
        "conda_self.install.run", return_value=CompletedProcess([], returncode)
    )
    _, _, code = conda_cli("self", "install", "example-plugin")

    assert code == returncode
    run.assert_called_once()
    (command,) = run.call_args.args
    assert command[3:7] == ["plugins", "install", "-n", "base"]
    assert "--override-frozen" not in command
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
    assert "Not conda plugin packages" in error
    assert history.read_bytes() == before_install
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
    marker = base_env / PREFIX_FROZEN_FILE
    marker.write_text(json.dumps({"message": "Frozen for maintenance"}))

    assert not is_installed(base_env, "conda-build")
    args = ("self", "install", "--yes", "conda-build")
    result = conda_cli_subprocess(
        base_env, *args, "--json", capture_output=True, text=True, check=False
    )
    assert result.returncode != 0
    assert "Frozen for maintenance" in json.loads(result.stdout)["error"]
    assert not is_installed(base_env, "conda-build")
    marker.unlink()

    conda_cli_subprocess(base_env, *args)
    assert is_installed(base_env, "conda-build")
