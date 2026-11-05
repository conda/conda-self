from __future__ import annotations

import json
from subprocess import CompletedProcess
from typing import TYPE_CHECKING

import pytest
from conda.base.context import context
from conda.core.prefix_data import PrefixData
from conda.exceptions import CondaValueError
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord

from conda_self.testing import conda_cli_subprocess

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


def test_help(conda_cli: CondaCLIFixture):
    out, err, exc = conda_cli("self", "update", "--help", raises=SystemExit)
    assert exc.value.code == 0


def test_update_plugin_invalid(conda_cli: CondaCLIFixture):
    conda_cli("self", "update", "--plugin", "conda-fake-solver", raises=CondaValueError)


@pytest.mark.parametrize(
    ("extra_args", "expected_flags", "unexpected_flags", "expected_json"),
    (
        pytest.param(
            ("--json",),
            ("--json", "--update-deps", "conda"),
            ("--update-specs", "--all"),
            {"success": True},
            id="json",
        ),
        pytest.param(
            ("--quiet", "--dry-run"),
            ("--quiet", "--dry-run", "--update-deps", "conda"),
            ("--update-specs", "--all"),
            None,
            id="quiet+dry-run",
        ),
        pytest.param(
            ("--plugin", "conda-libmamba-solver", "--quiet"),
            ("--quiet", "--update-deps", "conda-libmamba-solver"),
            ("--update-specs", "--all"),
            None,
            id="plugin",
        ),
        pytest.param(
            ("--all", "--quiet"),
            ("--quiet", "--all", "conda"),
            ("--update-specs", "--update-deps"),
            None,
            id="all",
        ),
    ),
)
def test_update_output_options(
    extra_args: tuple[str, ...],
    expected_flags: tuple[str, ...],
    unexpected_flags: tuple[str, ...],
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
        if not flag.startswith("--"):
            installed = PrefixData(context.root_prefix).get(flag)
            flag = f"{flag}>={installed.version}"
        assert flag in commands[0]
    for flag in unexpected_flags:
        assert flag not in commands[0]


@pytest.mark.parametrize(
    ("kwargs", "expected_flag", "unexpected_flags"),
    (
        pytest.param(
            {"update_dependencies": True},
            "--update-deps",
            ("--update-specs", "--all"),
            id="update-deps",
        ),
        pytest.param(
            {"update_all": True},
            "--all",
            ("--update-specs", "--update-deps"),
            id="all",
        ),
        pytest.param(
            {},
            "--update-specs",
            ("--update-deps", "--all"),
            id="update-specs",
        ),
    ),
)
def test_install_specs_update_flags(
    kwargs: dict[str, bool],
    expected_flag: str,
    unexpected_flags: tuple[str, ...],
    monkeypatch: MonkeyPatch,
) -> None:
    from conda_self.install import install_specs_in_protected_env

    commands: list[list[str]] = []

    def run(command: list[str]) -> CompletedProcess[str]:
        commands.append(command)
        return CompletedProcess(command, 0)

    monkeypatch.setattr("conda_self.install.run", run)

    assert install_specs_in_protected_env(["conda"], **kwargs) == 0
    assert expected_flag in commands[0]
    for flag in unexpected_flags:
        assert flag not in commands[0]


@pytest.mark.parametrize(
    "extra_args,expected",
    (
        pytest.param((), "conda (installed:", id="conda"),
        pytest.param(
            ("--plugin", "conda-libmamba-solver"),
            "conda-libmamba-solver (installed:",
            id="plugin",
        ),
        pytest.param(("--all",), "all installed packages", id="all"),
        pytest.param(
            ("--all", "--force-reinstall"),
            "all installed packages",
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


@pytest.mark.parametrize(
    "extra_args,package_name",
    (
        pytest.param((), "conda", id="conda"),
        pytest.param(("--force-reinstall",), "conda", id="reinstall"),
        pytest.param(
            ("--plugin", "conda-libmamba-solver"),
            "conda-libmamba-solver",
            id="plugin",
        ),
        pytest.param(("--all",), "conda", id="all"),
    ),
)
def test_update_specs_prevent_downgrades(
    extra_args: tuple[str, ...],
    package_name: str,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
) -> None:
    records = {
        name: PackageRecord(name=name, version=version, build="0", build_number=0)
        for name, version in (
            ("conda", "26.9.3"),
            ("conda-libmamba-solver", "26.7.0"),
        )
    }
    mocker.patch("conda.core.prefix_data.PrefixData.get", side_effect=records.get)
    mocker.patch(
        "conda_self.validate.conda_plugin_packages",
        return_value={"conda-libmamba-solver"},
    )
    install = mocker.patch(
        "conda_self.install.install_specs_in_protected_env", return_value=0
    )

    conda_cli("self", "update", *extra_args)

    specs = {
        spec.name: spec for spec in map(MatchSpec, install.call_args.kwargs["specs"])
    }
    spec = specs[package_name]
    installed = records[package_name]
    older, newer = {
        "conda": ("26.9.2", "26.9.4"),
        "conda-libmamba-solver": ("26.6.0", "26.7.1"),
    }[package_name]
    assert spec.match(installed)
    assert spec.match(PackageRecord.from_objects(installed, version=newer))
    assert not spec.match(PackageRecord.from_objects(installed, version=older))
