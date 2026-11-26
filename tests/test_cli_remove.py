from __future__ import annotations

import sys
from subprocess import CompletedProcess
from typing import TYPE_CHECKING

import pytest

from conda_self.exceptions import PluginRemoveError
from conda_self.testing import conda_cli_subprocess, is_installed

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


@pytest.fixture
def stub_uninstall_specs(monkeypatch: MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def run(command: list[str]) -> CompletedProcess[str]:
        calls.append(command[command.index("--yes") + 1 :])
        return CompletedProcess(command, 0)

    monkeypatch.setattr("conda_self.cli.main_remove.run", run)
    return calls


def test_help(conda_cli: CondaCLIFixture) -> None:
    out, err, exc = conda_cli("self", "remove", "--help", raises=SystemExit)
    assert exc.value.code == 0


@pytest.mark.parametrize("returncode", (0, 17))
def test_remove_preserves_native_options_and_exit_code(
    returncode: int,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
) -> None:
    run = mocker.patch(
        "conda_self.cli.main_remove.run", return_value=CompletedProcess([], returncode)
    )

    _, _, code = conda_cli("self", "remove", "--json", "--yes", "example-plugin")

    assert code == returncode
    run.assert_called_once_with(
        [
            sys.executable,
            "-m",
            "conda",
            "remove",
            f"--prefix={sys.prefix}",
            "--override-frozen",
            "--json",
            "--yes",
            "example-plugin",
        ]
    )


@pytest.mark.parametrize(
    "spec,force,raises",
    (
        ("conda", False, PluginRemoveError),
        ("conda-rattler-solver", False, PluginRemoveError),
        ("python", False, PluginRemoveError),
        ("conda", True, None),
        ("conda-rattler-solver", True, None),
        ("python", True, None),
        ("flask", False, None),
        ("flask", True, None),
    ),
)
def test_remove_validation(
    conda_cli: CondaCLIFixture,
    spec: str,
    force: bool,
    raises: type[Exception] | None,
    stub_uninstall_specs: list[list[str]],
) -> None:
    """Validation guard for permanent specs, overridden by ``--force``."""
    argv = ["self", "remove", "--yes", spec]
    if force:
        argv.insert(2, "--force")

    if raises is not None:
        conda_cli(*argv, raises=raises)
        assert stub_uninstall_specs == []
    else:
        conda_cli(*argv)
        assert stub_uninstall_specs == [[spec]]


@pytest.mark.parametrize(
    "spec,expect_warning",
    (
        ("conda", True),
        ("conda-rattler-solver", True),
        ("python", True),
        ("flask", False),
    ),
)
def test_force_warning_message(
    conda_cli: CondaCLIFixture,
    spec: str,
    expect_warning: bool,
    stub_uninstall_specs: list[list[str]],
) -> None:
    """``--force`` warns to stderr only when overriding permanent specs."""
    _out, err, _exc = conda_cli("self", "remove", "--yes", "--force", spec)
    assert ("Warning" in err and spec in err and "--force" in err) is expect_warning
    assert stub_uninstall_specs == [[spec]]


def test_remove_nonessential_plugin(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    base_env: Path,
    conda_channel: str,
) -> None:
    monkeypatch.setenv("CONDA_CHANNELS", conda_channel)

    conda_cli("install", "conda-build", "--yes", "--prefix", base_env)
    assert is_installed(base_env, "conda-build")
    conda_cli_subprocess(
        base_env,
        "self",
        "remove",
        "--yes",
        "conda-build",
    )
    assert not is_installed(base_env, "conda-build")
