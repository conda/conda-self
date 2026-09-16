from __future__ import annotations

import json
from subprocess import CompletedProcess
from typing import TYPE_CHECKING

import pytest
from conda.exceptions import CondaValueError, DryRunExit

from conda_self.testing import conda_cli_subprocess, is_installed

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture
    from pytest import MonkeyPatch


def test_help(conda_cli: CondaCLIFixture):
    out, err, exc = conda_cli("self", "install", "--help", raises=SystemExit)
    assert exc.value.code == 0


def test_install_plugin_dry_run(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    conda_channel: str,
):
    conda_cli(
        "self",
        "install",
        "--override-channels",
        "--channel",
        conda_channel,
        "--dry-run",
        "conda-libmamba-solver",
        raises=DryRunExit,
    )


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


@pytest.mark.parametrize("plugin_name", ("flask", "numpy"))
def test_install_not_plugins(
    plugin_name: str,
    monkeypatch: MonkeyPatch,
    base_env: Path,
    conda_channel: str,
):
    monkeypatch.setenv("CONDA_CHANNELS", conda_channel)

    result = conda_cli_subprocess(
        base_env, "info", "--json", capture_output=True, text=True
    )
    info = json.loads(result.stdout)
    assert info["sys.prefix"] == str(base_env)

    result = conda_cli_subprocess(
        base_env,
        "self",
        "install",
        "--yes",
        plugin_name,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "NotAPluginError" in result.stderr
    assert not is_installed(base_env, plugin_name)


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

    assert not is_installed(base_env, "conda-build")
    conda_cli_subprocess(
        base_env,
        "self",
        "install",
        "--yes",
        "conda-build",
    )
    assert is_installed(base_env, "conda-build")


@pytest.mark.parametrize("override", (False, True))
def test_install_temporary_channels(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    override: bool,
):
    from conda_self import install

    config = tmp_path / "condarc"
    original = "channels: [configured]\nchannel_priority: strict\n"
    config.write_text(original)
    monkeypatch.setenv("CONDARC", str(config))
    commands = []

    def run(command):
        commands.append(command)
        return CompletedProcess(command, 1)

    monkeypatch.setattr(install, "run", run)
    channels = [
        "https://packages.example.org/first",
        "https://packages.example.org/second",
    ]
    _, _, status = conda_cli(
        "self",
        "install",
        "-c",
        channels[0],
        "--channel",
        channels[1],
        *(("--override-channels",) if override else ()),
        "conda-example",
    )
    assert status == 1
    command = commands.pop()
    assert ("--override-channels" in command) is override
    assert [
        command[index + 1]
        for index, argument in enumerate(command)
        if argument == "--channel"
    ] == channels
    assert "configured" not in command
    assert config.read_text() == original


def test_default_install_does_not_forward_resolved_channels(
    conda_cli: CondaCLIFixture, monkeypatch: MonkeyPatch
):
    from conda_self import install

    commands = []

    def run(command):
        commands.append(command)
        return CompletedProcess(command, 1)

    monkeypatch.setattr(install, "run", run)
    _, _, status = conda_cli("self", "install", "conda-example")
    assert status == 1
    assert "--channel" not in commands[0]
    assert "--override-channels" not in commands[0]
