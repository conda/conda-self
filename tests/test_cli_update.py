from __future__ import annotations

import json
from subprocess import CompletedProcess
from typing import TYPE_CHECKING

import pytest
from conda.exceptions import CondaValueError

from conda_self.testing import conda_cli_subprocess

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture
    from pytest import MonkeyPatch


def test_help(conda_cli: CondaCLIFixture):
    out, err, exc = conda_cli("self", "update", "--help", raises=SystemExit)
    assert exc.value.code == 0


def test_update_plugin_invalid(conda_cli: CondaCLIFixture):
    conda_cli("self", "update", "--plugin", "conda-fake-solver", raises=CondaValueError)


@pytest.mark.parametrize(
    ("extra_args", "expected_flags", "expected_json"),
    (
        pytest.param(("--json",), ("--json",), {"success": True}, id="json"),
        pytest.param(
            ("--quiet", "--dry-run"),
            ("--quiet", "--dry-run"),
            None,
            id="quiet+dry-run",
        ),
    ),
)
def test_update_output_options(
    extra_args: tuple[str, ...],
    expected_flags: tuple[str, ...],
    expected_json: dict[str, bool] | None,
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def run(command: list[str]) -> CompletedProcess[str]:
        commands.append(command)
        if expected_json is not None:
            print(json.dumps(expected_json))
        return CompletedProcess(command, 0)

    monkeypatch.setattr("conda_self.install.run", run)

    out, _err, _exc = conda_cli("self", "update", *extra_args)

    if expected_json is None:
        assert out == ""
    else:
        assert json.loads(out) == expected_json
    for flag in expected_flags:
        assert flag in commands[0]


@pytest.mark.parametrize(
    "extra_args,expected",
    (
        pytest.param((), "conda (installed:", id="conda"),
        pytest.param(
            ("--plugin", "conda-libmamba-solver"),
            "conda-libmamba-solver (installed:",
            id="plugin",
        ),
        pytest.param(("--all",), "conda (installed:", id="all"),
        pytest.param(
            ("--all", "--force-reinstall"),
            "conda (installed:",
            id="all+force-reinstall",
        ),
    ),
)
def test_update(
    extra_args: tuple[str, ...],
    expected: str,
    monkeypatch: MonkeyPatch,
    base_env: Path,
    conda_channel: str,
):
    monkeypatch.setenv("CONDA_CHANNELS", conda_channel)

    result = conda_cli_subprocess(
        base_env,
        "self",
        "update",
        *extra_args,
        "--dry-run",
        "--yes",
        capture_output=True,
        text=True,
    )
    assert "Updating" in result.stdout
    assert expected in result.stdout
