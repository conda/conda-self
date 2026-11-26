"""Tests for base-protection health check."""

from __future__ import annotations

import json
import shutil
import sys
from argparse import Namespace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from conda.base.constants import PREFIX_FROZEN_FILE
from conda.base.context import context
from conda.core.prefix_data import PrefixData
from conda.exceptions import (
    CondaOSError,
    CondaSystemExit,
)
from ruamel.yaml import YAML

from conda_self.constants import RESET_FILE_BASE_PROTECTION, RESET_FILE_INSTALLER
from conda_self.health_checks import base_protection
from conda_self.plugin import conda_health_checks

if TYPE_CHECKING:
    from pytest import CaptureFixture, MonkeyPatch


def clone_metadata(source: str, target: str, **kwargs):
    from conda.misc import untracked

    shutil.copytree(
        Path(source) / "conda-meta", Path(target) / "conda-meta", dirs_exist_ok=True
    )
    for filename in untracked(source):
        destination = Path(target) / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(source) / filename, destination)


@pytest.fixture
def fake_base_env(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    """Create a fake base environment by patching sys.prefix."""
    conda_meta = tmp_path / "conda-meta"
    conda_meta.mkdir()
    monkeypatch.setattr(sys, "prefix", str(tmp_path))
    return tmp_path


@pytest.fixture
def protected_base_env(fake_base_env: Path) -> Path:
    """Create a fake protected (frozen) base environment."""
    frozen_file = fake_base_env / PREFIX_FROZEN_FILE
    frozen_file.write_text("{}")
    return fake_base_env


@pytest.fixture
def reset_calls():
    return []


@pytest.fixture
def base_protection_env(
    fake_base_env: Path,
    monkeypatch: MonkeyPatch,
    reset_calls: list,
) -> Path:
    """Use real package metadata, exports, and configuration for protection tests."""
    conda_meta = fake_base_env / "conda-meta"
    (conda_meta / "history").touch()
    for name in ("conda", "user-package"):
        filename = f"{name}-1.0-0.conda"
        (conda_meta / f"{name}-1.0-0.json").write_text(
            json.dumps(
                {
                    "name": name,
                    "version": "1.0",
                    "build": "0",
                    "build_number": 0,
                    "subdir": "noarch",
                    "fn": filename,
                    "url": f"https://packages.example.test/noarch/{filename}",
                    "depends": [],
                }
            )
        )
    PrefixData._cache_.clear()
    destination = fake_base_env / "envs" / "default"
    monkeypatch.setattr(
        type(context), "envs_dirs", property(lambda self: (str(destination.parent),))
    )
    condarc = fake_base_env / "user.condarc"
    condarc.write_text("default_activation_env: work\nchannels:\n  - conda-forge\n")
    monkeypatch.setattr("conda.base.context.user_rc_path", str(condarc))
    monkeypatch.setattr("conda.misc.clone_env", clone_metadata)
    monkeypatch.setattr(
        "conda.core.envs_manager.get_user_environments_txt_file",
        lambda *args: str(fake_base_env.parent / "environments.txt"),
    )
    monkeypatch.setattr(
        "conda_self.reset.reset", lambda **kwargs: reset_calls.append(kwargs)
    )
    return fake_base_env


@pytest.mark.parametrize(
    "env_fixture, expected_output, unexpected_output",
    [
        ("tmp_path", "skipping", None),
        ("protected_base_env", "marked as frozen", "not marked as frozen"),
        ("fake_base_env", "not marked as frozen", None),
    ],
    ids=["non-base", "protected", "unprotected"],
)
def test_check(
    env_fixture: str,
    expected_output: str,
    unexpected_output: str | None,
    request: pytest.FixtureRequest,
    capsys: CaptureFixture,
):
    prefix = str(request.getfixturevalue(env_fixture))
    PrefixData._cache_.clear()
    base_protection.check(prefix, False)

    captured = capsys.readouterr()
    assert expected_output in captured.out.lower()
    if unexpected_output:
        assert unexpected_output not in captured.out.lower()


@pytest.mark.parametrize(
    "env_fixture, expected_output",
    [
        ("tmp_path", "Skipping"),
        ("protected_base_env", "already protected"),
    ],
    ids=["non-base", "already-protected"],
)
def test_fix_skips(
    env_fixture: str,
    expected_output: str,
    request: pytest.FixtureRequest,
    capsys: CaptureFixture,
):
    prefix = str(request.getfixturevalue(env_fixture))
    confirm_called: list[str] = []

    PrefixData._cache_.clear()
    result = base_protection.fix(prefix, Namespace(), confirm_called.append)

    assert result == 0
    assert expected_output in capsys.readouterr().out
    assert confirm_called == []


def test_fix_calls_confirm_callback(base_protection_env: Path):
    confirm_called: list[str] = []

    class UserCancelled(Exception):
        pass

    def confirm(msg: str) -> None:
        confirm_called.append(msg)
        raise UserCancelled()

    PrefixData._cache_.clear()
    with pytest.raises(UserCancelled):
        base_protection.fix(str(base_protection_env), Namespace(), confirm)

    assert confirm_called == ["Proceed?"]


@pytest.mark.parametrize(
    "is_environment", [True, False], ids=["environment", "directory"]
)
def test_fix_cancel_preserves_existing_destination(
    base_protection_env: Path,
    monkeypatch: MonkeyPatch,
    reset_calls: list,
    is_environment: bool,
):
    destination = base_protection_env / "envs" / "default"
    destination.mkdir(parents=True)
    if is_environment:
        (destination / "conda-meta").mkdir()
        (destination / "conda-meta" / "history").touch()
    sentinel = destination / "keep.txt"
    sentinel.write_text("existing user data\n")
    prompts: list[str] = []

    def confirm(message: str):
        prompts.append(message)
        if len(prompts) == 2:
            raise CondaSystemExit("Aborted")

    def unexpected_clone(*args, **kwargs):
        pytest.fail("Cloning must wait for destination confirmation")

    monkeypatch.setattr("conda.misc.clone_env", unexpected_clone)

    with pytest.raises(CondaSystemExit, match="Aborted"):
        base_protection.fix(str(base_protection_env), Namespace(), confirm)

    assert len(prompts) == 2
    assert sentinel.read_text() == "existing user data\n"
    assert not (base_protection_env / PREFIX_FROZEN_FILE).exists()
    assert reset_calls == []


def test_fix_replaces_existing_environment_after_confirmation(
    base_protection_env: Path,
    monkeypatch: MonkeyPatch,
    reset_calls: list,
):
    destination = base_protection_env / "envs" / "default"
    (destination / "conda-meta").mkdir(parents=True)
    (destination / "conda-meta" / "history").touch()
    sentinel = destination / "old-data.txt"
    sentinel.write_text("old environment\n")
    prompts: list[str] = []

    def confirm(message: str):
        assert sentinel.read_text() == "old environment\n"
        prompts.append(message)

    def clone(source: str, target: str, **kwargs):
        assert len(prompts) == 2
        assert source == str(base_protection_env)
        assert target == str(destination)
        assert not destination.exists()
        clone_metadata(source, target)
        (destination / "cloned-data.txt").write_text("cloned environment\n")

    monkeypatch.setattr("conda.misc.clone_env", clone)

    assert base_protection.fix(str(base_protection_env), Namespace(), confirm) == 0

    assert "Remove and recreate?" in prompts[1]
    assert not sentinel.exists()
    assert (destination / "cloned-data.txt").read_text() == "cloned environment\n"
    assert len(reset_calls) == 1
    assert (base_protection_env / PREFIX_FROZEN_FILE).is_file()
    assert YAML(typ="safe").load(
        (base_protection_env / "user.condarc").read_text()
    ) == {
        "default_activation_env": str(destination),
        "channels": ["conda-forge"],
    }


@pytest.mark.parametrize("failing_operation", ["clone", "reset"])
def test_fix_preserves_recovery_snapshot_after_failure(
    base_protection_env: Path,
    monkeypatch: MonkeyPatch,
    failing_operation: str,
):
    monkeypatch.setitem(vars(context), "prefix_data_interoperability", True)
    initial_names = {
        record.name
        for record in PrefixData(
            base_protection_env, interoperability=True
        ).iter_records()
    }
    conda_meta = base_protection_env / "conda-meta"
    snapshot = conda_meta / RESET_FILE_BASE_PROTECTION
    snapshots_before_clone: list[str] = []

    def clone(*args, **kwargs):
        snapshots_before_clone.append(snapshot.read_text())
        if failing_operation == "clone":
            raise OSError("clone failed")
        clone_metadata(*args, **kwargs)

    def reset(**kwargs):
        (conda_meta / "user-package-1.0-0.json").unlink()
        raise OSError("reset failed")

    monkeypatch.setattr("conda.misc.clone_env", clone)
    monkeypatch.setattr("conda_self.reset.reset", reset)

    with pytest.raises(OSError, match=f"{failing_operation} failed"):
        base_protection.fix(str(base_protection_env), Namespace(), lambda msg: None)

    assert context.prefix_data_interoperability is True
    expected_names = (
        initial_names - {"user-package"}
        if failing_operation == "reset"
        else initial_names
    )
    for mode in (False, True):
        assert {
            record.name
            for record in PrefixData(
                base_protection_env, interoperability=mode
            ).iter_records()
        } == expected_names
    assert len(snapshots_before_clone) == 1
    assert snapshot.read_text() == snapshots_before_clone[0]
    assert {
        line for line in snapshot.read_text().splitlines() if not line.startswith("#")
    } == {
        "@EXPLICIT",
        "https://packages.example.test/noarch/conda-1.0-0.conda",
        "https://packages.example.test/noarch/user-package-1.0-0.conda",
    }
    assert not (base_protection_env / PREFIX_FROZEN_FILE).exists()


def test_fix_freeze_failure_preserves_activation_config(
    base_protection_env: Path,
    monkeypatch: MonkeyPatch,
    reset_calls: list,
):
    condarc = base_protection_env / "user.condarc"
    original_config = condarc.read_bytes()
    frozen_file = base_protection_env / PREFIX_FROZEN_FILE
    write_text = Path.write_text

    def fail_freeze(path, *args, **kwargs):
        if path == frozen_file:
            raise PermissionError("Cannot write frozen marker")
        return write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_freeze)

    with pytest.raises(CondaOSError, match="Could not protect the base environment"):
        base_protection.fix(str(base_protection_env), Namespace(), lambda msg: None)

    assert len(reset_calls) == 1
    assert not frozen_file.exists()
    assert condarc.read_bytes() == original_config


@pytest.mark.parametrize(
    "create_snapshot, expect_names_only, expected_keep",
    [
        (
            True,
            True,
            {"conda", "conda-self", "mamba", "pip"},
        ),
        (
            False,
            True,
            {"conda", "conda-self"},
        ),
    ],
    ids=[
        "with-installer-snapshot",
        "without-installer-snapshot",
    ],
)
def test_fix_reset_strategy(
    base_protection_env: Path,
    reset_calls: list,
    create_snapshot: bool,
    expect_names_only: bool,
    expected_keep: set[str],
):
    for name in ("conda-self", "mamba", "pip"):
        (base_protection_env / "conda-meta" / f"{name}-1.0-0.json").write_text(
            json.dumps(
                {
                    "name": name,
                    "version": "1.0",
                    "build": "0",
                    "build_number": 0,
                    "subdir": "noarch",
                    "depends": [],
                    "files": [],
                    "fn": f"{name}-1.0-0.conda",
                    "url": f"https://packages.example.test/noarch/{name}-1.0-0.conda",
                }
            )
        )
    if create_snapshot:
        snapshot = base_protection_env / "conda-meta" / RESET_FILE_INSTALLER
        snapshot.write_text(
            "@EXPLICIT\n"
            "https://conda.anaconda.org/conda-forge/noarch/"
            "mamba-1.5.0-pyh_0.conda#0123456789abcdef0123456789abcdef\n"
            "https://conda.anaconda.org/conda-forge/noarch/"
            "pip-24.0-pyhd8ed1ab_0.conda\n"
        )

    base_protection.fix(str(base_protection_env), Namespace(), lambda msg: None)

    assert len(reset_calls) == 1
    assert "snapshot" not in reset_calls[0]
    assert expected_keep <= reset_calls[0]["uninstallable_packages"]


@pytest.mark.parametrize("quiet", [False, True], ids=["normal", "quiet"])
def test_fix_without_exportable_snapshot_preserves_environments(
    base_protection_env: Path,
    monkeypatch: MonkeyPatch,
    reset_calls: list,
    quiet: bool,
):
    from conda.exceptions import CondaValueError

    destination = base_protection_env / "envs" / "default"
    destination.mkdir(parents=True)
    sentinel = destination / "keep.txt"
    sentinel.write_text("existing user data")
    monkeypatch.setitem(vars(context), "quiet", quiet)

    def unexportable(*args, **kwargs):
        raise CondaValueError("Cannot export this environment")

    monkeypatch.setattr(
        context.plugin_manager, "get_environment_exporter_by_format", unexportable
    )
    with pytest.raises(CondaValueError, match="recovery snapshot"):
        base_protection.fix(str(base_protection_env), Namespace(), lambda message: None)
    assert sentinel.read_text() == "existing user data"
    assert reset_calls == []
    assert not (base_protection_env / PREFIX_FROZEN_FILE).exists()


def test_health_check_registered():
    health_checks = list(conda_health_checks())

    assert len(health_checks) == 1
    hc = health_checks[0]
    assert hc.name == "base-protection"
    assert hc.action == base_protection.check
    assert hc.fixer == base_protection.fix
    assert hc.summary is not None
    assert hc.fix is not None
