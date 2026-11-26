from __future__ import annotations

import io
import json
import shutil
import sys
import tarfile
from argparse import Namespace
from pathlib import Path

import pytest
from conda.base.constants import PREFIX_FROZEN_FILE
from conda.base.context import context
from conda.core.prefix_data import PrefixData
from conda.exceptions import CondaSystemExit, DryRunExit
from conda.history import History
from conda.models.records import PrefixRecord

from conda_self.health_checks import base_protection


@pytest.fixture
def migration_env(tmp_path, monkeypatch, tmp_pkgs_dir):
    base = tmp_path / "base"
    meta = base / "conda-meta"
    meta.mkdir(parents=True)
    channel = tmp_path / "channel" / "noarch"
    channel.mkdir(parents=True)
    packages = (
        ("conda", ("shared >=1", "manager-helper >=1"), False),
        ("conda-self", ("conda",), True),
        ("third-party-plugin", ("conda", "plugin-helper"), True),
        ("manager-helper", (), False),
        ("plugin-helper", (), False),
        ("shared", (), False),
        ("user-package", ("shared >=1",), False),
        ("conda-dependent-tool", ("conda",), False),
    )
    for name, depends, plugin in packages:
        index = dict(
            name=name,
            version="1.2",
            build="build_0",
            build_number=0,
            subdir="noarch",
            depends=depends,
        )
        payload = f"share/{name}.txt"
        members = {payload: f"{name} installed data\n".encode()}
        if plugin:
            members[
                f"lib/python3.13/site-packages/{name}.dist-info/entry_points.txt"
            ] = b"[conda]\nexample = example:plugin\n"
            members[f"lib/python3.13/site-packages/{name}.dist-info/METADATA"] = (
                f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.2\n".encode()
            )
        archive = channel / f"{name}-1.2-build_0.tar.bz2"
        package_members = {
            **members,
            "info/index.json": json.dumps(index).encode(),
            "info/files": ("\n".join(members) + "\n").encode(),
        }
        with tarfile.open(archive, "w:bz2") as output:
            for path, contents in package_members.items():
                member = tarfile.TarInfo(path)
                member.size = len(contents)
                output.addfile(member, io.BytesIO(contents))
        for path, contents in members.items():
            target = base / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(contents)
        record = PrefixRecord(
            **index,
            fn=archive.name,
            url=archive.as_uri(),
            channel=channel.parent.as_uri(),
            files=tuple(members),
        )
        (meta / f"{name}-1.2-build_0.json").write_text(json.dumps(record.dump()))
    (meta / "history").write_text(
        "==> 2026-11-26 10:00:00 <==\n"
        "# cmd: conda install user-package conda-dependent-tool\n"
        "# update specs: ['user-package', 'conda-dependent-tool']\n"
    )
    (base / "notes.txt").write_text("keep this untracked file\n")
    destination = base / "envs" / "default"
    condarc = tmp_path / "condarc"
    condarc.write_text("default_activation_env: work\n")
    monkeypatch.setattr(sys, "prefix", str(base))
    monkeypatch.setattr(
        type(context), "envs_dirs", property(lambda self: (str(destination.parent),))
    )
    monkeypatch.setattr("conda.base.context.user_rc_path", str(condarc))
    monkeypatch.setattr(
        "conda.core.envs_manager.get_user_environments_txt_file",
        lambda *args: str(tmp_path / "environments.txt"),
    )
    return base, destination, condarc


@pytest.mark.parametrize("quiet", [False, True])
def test_full_plan_precedes_confirmation(migration_env, capsys, monkeypatch, quiet):
    base, destination, condarc = migration_env
    original = condarc.read_bytes()
    monkeypatch.setitem(vars(context), "quiet", quiet)

    def decline(message):
        output = capsys.readouterr().out
        assert "Migration plan" in output
        assert "Retained in base" in output
        assert "Installed in default" in output
        assert "Unavailable in default" in output
        assert "Removed from both environments" in output
        assert "conda-dependent-tool" in output
        assert "third-party-plugin" in output
        assert "user-package" in output
        assert "1.2" in output
        assert "build_0" in output
        assert "Versions and builds will not change" in output
        raise CondaSystemExit("Aborted")

    with pytest.raises(CondaSystemExit):
        base_protection.fix(str(base), Namespace(), decline)
    assert not destination.exists()
    assert not (base / PREFIX_FROZEN_FILE).exists()
    assert condarc.read_bytes() == original
    assert not (base / "conda-meta" / "base-protection-state.explicit.txt").exists()


def test_dry_run_prints_plan_without_changes(migration_env, monkeypatch, capsys):
    base, destination, condarc = migration_env
    original = condarc.read_bytes()
    monkeypatch.setitem(vars(context), "dry_run", True)

    def confirm(message):
        raise DryRunExit()

    with pytest.raises(DryRunExit):
        base_protection.fix(str(base), Namespace(), confirm)
    assert "Removed from both environments" in capsys.readouterr().out
    assert not destination.exists()
    assert not (base / PREFIX_FROZEN_FILE).exists()
    assert condarc.read_bytes() == original


@pytest.mark.parametrize("interoperability", [False, True])
def test_migration_uses_real_clone_and_unlink_transactions(
    migration_env, monkeypatch, interoperability
):
    base, destination, condarc = migration_env
    monkeypatch.setitem(vars(context), "prefix_data_interoperability", interoperability)
    source = {record.name: record for record in PrefixData(base).iter_records()}
    assert base_protection.fix(str(base), Namespace(), lambda message: None) == 0
    expected_base = {
        "conda",
        "conda-self",
        "third-party-plugin",
        "manager-helper",
        "plugin-helper",
        "shared",
    }
    for mode in (False, True):
        assert {
            record.name
            for record in PrefixData(base, interoperability=mode).iter_records()
        } == expected_base
    actual = {
        record.name: record
        for record in PrefixData(destination).reload().iter_records()
    }
    assert set(actual) == {"user-package", "shared"}
    for name, record in actual.items():
        assert (record.version, record.build, record.channel.base_url) == (
            source[name].version,
            source[name].build,
            source[name].channel.base_url,
        )
    assert not (destination / "share" / "conda.txt").exists()
    assert not (destination / "share" / "third-party-plugin.txt").exists()
    assert (destination / "share" / "user-package.txt").is_file()
    assert (destination / "notes.txt").read_text() == "keep this untracked file\n"
    assert set(History(str(destination)).get_requested_specs_map()) == {"user-package"}
    assert (base / PREFIX_FROZEN_FILE).exists()
    assert str(destination) in condarc.read_text()
    assert context.prefix_data_interoperability is interoperability


def test_incomplete_clone_does_not_reset_base(migration_env, monkeypatch):
    base, destination, condarc = migration_env
    original_config = condarc.read_bytes()
    original_records = {record.name for record in PrefixData(base).iter_records()}

    def clone(source, target, **kwargs):
        shutil.copytree(base / "conda-meta", Path(target) / "conda-meta")
        (Path(target) / "conda-meta" / "user-package-1.2-build_0.json").unlink()

    monkeypatch.setattr("conda.misc.clone_env", clone)
    from conda.exceptions import CondaValueError

    with pytest.raises(CondaValueError, match="match the migration plan"):
        base_protection.fix(str(base), Namespace(), lambda message: None)
    assert {
        record.name for record in PrefixData(base).reload().iter_records()
    } == original_records
    assert not (base / PREFIX_FROZEN_FILE).exists()
    assert condarc.read_bytes() == original_config


def test_empty_default_preserves_untracked_files(migration_env):
    base, destination, _ = migration_env
    (base / "conda-meta" / "user-package-1.2-build_0.json").unlink()
    (base / "share" / "user-package.txt").unlink()
    assert base_protection.fix(str(base), Namespace(), lambda message: None) == 0
    assert list(PrefixData(destination).reload().iter_records()) == []
    assert (destination / "notes.txt").is_file()
    assert History(str(destination)).get_requested_specs_map() == {}


def test_existing_cached_destination_is_replaced(migration_env):
    base, destination, _ = migration_env
    (destination / "conda-meta").mkdir(parents=True)
    (destination / "conda-meta" / "history").touch()
    old = PrefixRecord(
        name="old-package",
        version="9",
        build="0",
        build_number=0,
        subdir="noarch",
        files=(),
    )
    (destination / "conda-meta" / "old-package-9-0.json").write_text(
        json.dumps(old.dump())
    )
    for mode in (False, True):
        assert {
            r.name
            for r in PrefixData(destination, interoperability=mode).iter_records()
        } == {"old-package"}
    assert base_protection.fix(str(base), Namespace(), lambda message: None) == 0
    for mode in (False, True):
        assert {
            r.name
            for r in PrefixData(destination, interoperability=mode).iter_records()
        } == {"shared", "user-package"}


def test_external_packages_keep_runtime_libraries(migration_env):
    base, destination, _ = migration_env
    metadata = base / "lib/python3.13/site-packages/external_app-1.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: external-app\nVersion: 1\nRequires-Dist: shared\n"
    )
    assert base_protection.fix(str(base), Namespace(), lambda message: None) == 0
    assert {r.name for r in PrefixData(destination).reload().iter_records()} == {
        "user-package",
        "shared",
        "manager-helper",
        "plugin-helper",
    }
    assert (destination / metadata.relative_to(base) / "METADATA").exists()


def test_external_requirement_on_management_stops_before_confirmation(migration_env):
    from conda.exceptions import CondaValueError

    base, destination, condarc = migration_env
    metadata = base / "lib/python3.13/site-packages/external_app-1.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: external-app\nVersion: 1\nRequires-Dist: conda\n"
    )
    original = condarc.read_bytes()

    def unexpected_confirm(message):
        pytest.fail(
            "An invalid external dependency must be rejected before confirmation"
        )

    with pytest.raises(CondaValueError, match="External packages require"):
        base_protection.fix(str(base), Namespace(), unexpected_confirm)
    assert not destination.exists()
    assert condarc.read_bytes() == original


@pytest.mark.parametrize(
    "field,value",
    [("version", "2.0"), ("depends", ["shared >=2"]), ("files", ["share/changed.txt"])],
)
def test_base_change_during_confirmation_cancels_migration(migration_env, field, value):
    from conda.exceptions import CondaValueError

    base, destination, condarc = migration_env
    original = condarc.read_bytes()

    def change_source(message):
        path = base / "conda-meta" / "user-package-1.2-build_0.json"
        data = json.loads(path.read_text())
        data[field] = value
        path.write_text(json.dumps(data))

    with pytest.raises(CondaValueError, match="Base changed"):
        base_protection.fix(str(base), Namespace(), change_source)
    assert not destination.exists()
    assert condarc.read_bytes() == original


@pytest.mark.parametrize(
    "field,value",
    [("depends", ["shared >=2"]), ("files", ["share/changed.txt"])],
)
def test_reset_rejects_changed_metadata_before_removing_packages(
    migration_env, field, value
):
    from conda.exceptions import CondaValueError

    from conda_self.reset import reset

    base, _, _ = migration_env
    expected = tuple(PrefixData(base, interoperability=False).iter_records())
    path = base / "conda-meta" / "user-package-1.2-build_0.json"
    metadata = json.loads(path.read_text())
    metadata[field] = value
    path.write_text(json.dumps(metadata))

    with pytest.raises(CondaValueError, match="Base changed"):
        reset(prefix=str(base), expected_records=expected)

    assert (base / "share" / "user-package.txt").is_file()
    assert path.is_file()


@pytest.mark.parametrize("dry_run", [False, True])
def test_destination_resolution_does_not_create_directories(
    migration_env, monkeypatch, dry_run
):
    from conda.core.prefix_data import PrefixData as RealPrefixData

    base, _, _ = migration_env
    parent = base / "new-environments"
    monkeypatch.setattr(
        type(context), "envs_dirs", property(lambda self: (str(parent),))
    )
    # Exercise the original destination lookup, not the migration fixture's stub.
    from conda.base.context import locate_prefix_by_name
    from conda.core.prefix_data import first_writable_envs_dir
    from conda.exceptions import EnvironmentNameNotFound

    def real_from_name(name):
        try:
            return RealPrefixData(locate_prefix_by_name(name))
        except EnvironmentNameNotFound:
            return RealPrefixData(Path(first_writable_envs_dir(), name))

    monkeypatch.setattr(RealPrefixData, "from_name", real_from_name)
    monkeypatch.setitem(vars(context), "dry_run", dry_run)

    def decline(message):
        assert not parent.exists()
        raise CondaSystemExit("Aborted")

    with pytest.raises(CondaSystemExit):
        base_protection.fix(str(base), Namespace(), decline)
    assert not parent.exists()


@pytest.mark.parametrize("stop_at", ["confirmation", "clone"])
def test_interoperability_is_restored_after_interrupted_migration(
    migration_env, monkeypatch, stop_at
):
    base, destination, _ = migration_env
    monkeypatch.setitem(vars(context), "prefix_data_interoperability", True)

    def confirm(message):
        assert context.prefix_data_interoperability is False
        if stop_at == "confirmation":
            raise CondaSystemExit("Aborted")

    def clone(*args, **kwargs):
        assert context.prefix_data_interoperability is False
        raise CondaSystemExit("Aborted")

    monkeypatch.setattr("conda.misc.clone_env", clone)
    with pytest.raises(CondaSystemExit, match="Aborted"):
        base_protection.fix(str(base), Namespace(), confirm)
    assert context.prefix_data_interoperability is True
    assert not destination.exists()


def test_missing_untracked_file_prevents_base_reset(migration_env, monkeypatch):
    from conda.exceptions import CondaValueError
    from conda.misc import clone_env

    base, destination, condarc = migration_env
    original = condarc.read_bytes()

    def incomplete_clone(*args, **kwargs):
        result = clone_env(*args, **kwargs)
        (destination / "notes.txt").unlink()
        return result

    monkeypatch.setattr("conda.misc.clone_env", incomplete_clone)
    with pytest.raises(CondaValueError, match="Untracked files"):
        base_protection.fix(str(base), Namespace(), lambda message: None)
    assert (base / "conda-meta" / "user-package-1.2-build_0.json").exists()
    assert condarc.read_bytes() == original


def test_base_change_during_clone_prevents_unplanned_removal(
    migration_env, monkeypatch
):
    from conda.exceptions import CondaValueError

    prepare = base_protection._prepare_default
    base, destination, condarc = migration_env
    original = condarc.read_bytes()

    def changed_source(*args, **kwargs):
        prepare(*args, **kwargs)
        record = PrefixRecord(
            name="late-package",
            version="1",
            build="0",
            build_number=0,
            subdir="noarch",
            files=(),
        )
        (base / "conda-meta" / "late-package-1-0.json").write_text(
            json.dumps(record.dump())
        )

    monkeypatch.setattr(base_protection, "_prepare_default", changed_source)
    with pytest.raises(CondaValueError, match="Base changed"):
        base_protection.fix(str(base), Namespace(), lambda message: None)
    assert (base / "conda-meta" / "late-package-1-0.json").exists()
    assert (base / "conda-meta" / "user-package-1.2-build_0.json").exists()
    assert condarc.read_bytes() == original


def test_retry_after_freeze_failure_preserves_default_and_snapshot(
    migration_env, monkeypatch
):
    from conda.exceptions import CondaOSError, CondaValueError

    base, destination, _ = migration_env
    write_text = Path.write_text

    def fail_freeze(path, *args, **kwargs):
        if path == base / PREFIX_FROZEN_FILE:
            raise PermissionError("Cannot write frozen marker")
        return write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_freeze)
    with pytest.raises(CondaOSError, match="Restore base with"):
        base_protection.fix(str(base), Namespace(), lambda message: None)
    snapshot = base / "conda-meta" / "base-protection-state.explicit.txt"
    original = snapshot.read_bytes()
    user_record = destination / "conda-meta" / "user-package-1.2-build_0.json"
    record = user_record.read_bytes()
    with pytest.raises(CondaValueError, match="earlier migration"):
        base_protection.fix(str(base), Namespace(), lambda message: None)
    assert snapshot.read_bytes() == original
    assert user_record.read_bytes() == record
