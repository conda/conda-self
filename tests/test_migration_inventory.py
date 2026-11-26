from __future__ import annotations

from pathlib import Path

import pytest
from conda.common.path import get_python_site_packages_short_path
from conda.exceptions import CondaValueError
from conda.models.records import PrefixRecord

SITE_PACKAGES = get_python_site_packages_short_path("3.13")


def record(name: str, *files: str, version: str = "1.0") -> PrefixRecord:
    return PrefixRecord(
        name=name,
        version=version,
        build="0",
        build_number=0,
        subdir="noarch",
        files=files,
    )


def distribution(
    prefix: Path,
    name: str,
    *,
    parent: str = SITE_PACKAGES,
    directory: str | None = None,
    requirements: tuple[str, ...] = (),
    entry_points: str = "",
) -> tuple[str, ...]:
    relative = Path(parent, directory or f"{name}-1.0.dist-info")
    metadata = prefix / relative
    metadata.mkdir(parents=True)
    metadata_name = "PKG-INFO" if relative.name.endswith(".egg-info") else "METADATA"
    contents = f"Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n"
    contents += "".join(f"Requires-Dist: {item}\n" for item in requirements)
    (metadata / metadata_name).write_text(contents)
    files = [str(relative / metadata_name)]
    if entry_points:
        (metadata / "entry_points.txt").write_text(entry_points)
        files.append(str(relative / "entry_points.txt"))
    if relative.name.endswith(".dist-info"):
        files.append(str(relative / "RECORD"))
        (metadata / "RECORD").write_text(
            "".join(
                f"{Path(filename).relative_to(parent).as_posix()},,\n"
                for filename in files
            )
        )
    return tuple(files)


@pytest.mark.parametrize("entry_points_only", [False, True])
def test_discovers_owned_plugin_and_external_requirements(
    tmp_path: Path, entry_points_only: bool
):
    from conda_self.migration_inventory import inspect_migration_inventory

    owned_files = distribution(
        tmp_path,
        "plugin-dist",
        entry_points="[conda]\nplugin = never_import_this:plugin\n",
    )
    if entry_points_only:
        owned_files = tuple(
            filename
            for filename in owned_files
            if filename.endswith("entry_points.txt")
        )
    helper_files = distribution(tmp_path, "helper-dist")
    distribution(
        tmp_path, "ordinary", requirements=("helper-dist>=1", "external-helper")
    )
    distribution(tmp_path, "external-helper", requirements=("plugin-dist",))
    inventory = inspect_migration_inventory(
        tmp_path,
        [
            record("python", version="3.13"),
            record("plugin-package", *owned_files),
            record("helper-package", *helper_files),
        ],
    )

    assert inventory.plugin_names == frozenset({"plugin-package"})
    assert inventory.external_packages == ("external-helper==1.0", "ordinary==1.0")
    assert inventory.external_required_names == frozenset(
        {"helper-package", "plugin-package"}
    )


def test_preserves_ownership_of_multiple_distributions_in_one_package(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    helper_files = distribution(tmp_path, "bundled-helper")
    plugin_files = distribution(
        tmp_path,
        "bundled-plugin",
        entry_points="[conda]\nplugin = never_import_this:plugin\n",
    )
    distribution(
        tmp_path, "external", requirements=("bundled-helper", "bundled-plugin")
    )

    inventory = inspect_migration_inventory(
        tmp_path, [record("plugin-package", *helper_files, *plugin_files)]
    )

    assert inventory.plugin_names == frozenset({"plugin-package"})
    assert inventory.external_packages == ("external==1.0",)
    assert inventory.external_required_names == frozenset({"plugin-package"})


@pytest.mark.parametrize("suffix", ["dist-info", "egg-info"])
def test_rejects_external_plugins_without_prefix_loader(tmp_path: Path, suffix: str):
    from conda_self.migration_inventory import inspect_migration_inventory

    distribution(
        tmp_path,
        "external-plugin",
        directory=f"external_plugin-1.0.{suffix}",
        entry_points="[conda]\nplugin = never_import_this:plugin\n",
    )
    with pytest.raises(CondaValueError, match="external-plugin"):
        inspect_migration_inventory(tmp_path, [record("python", version="3.13")])


def test_discovers_site_packages_from_record_files(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    owned_files = distribution(tmp_path, "owned", parent="Lib/site-packages")
    distribution(
        tmp_path, "external", parent="Lib/site-packages", requirements=("native_lib",)
    )
    inventory = inspect_migration_inventory(
        tmp_path, [record("owned-package", *owned_files), record("native-lib")]
    )

    assert inventory.external_packages == ("external==1.0",)
    assert inventory.external_required_names == frozenset({"native-lib"})


def test_uses_python_record_site_packages_path(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    python = record("python", version="3.13")
    python.python_site_packages_path = "custom/python-libraries"
    distribution(tmp_path, "external", parent=python.python_site_packages_path)

    inventory = inspect_migration_inventory(tmp_path, [python])

    assert inventory.external_packages == ("external==1.0",)


@pytest.mark.parametrize("owned", [False, True])
def test_empty_conda_entry_point_group_is_not_a_plugin(tmp_path: Path, owned: bool):
    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(tmp_path, "ordinary", entry_points="[conda]\n")
    records = [record("python", version="3.13")]
    if owned:
        records.append(record("ordinary-package", *files))

    inventory = inspect_migration_inventory(tmp_path, records)

    assert inventory.plugin_names == frozenset()
    assert inventory.external_packages == (() if owned else ("ordinary==1.0",))


@pytest.mark.parametrize(
    "entry_points, is_plugin",
    [
        ("[DEFAULT]\nplugin = never_import_this:plugin\n[conda]\n", False),
        ("[DEFAULT]\nplugin = never_import_this:plugin\n[other]\nx = x:main\n", False),
        (
            (
                "[DEFAULT]\nplugin = never_import_this:plugin\n"
                "[conda]\nplugin = never_import_this:plugin\n"
            ),
            True,
        ),
    ],
)
def test_entry_point_groups_do_not_inherit_defaults(
    tmp_path: Path, entry_points: str, is_plugin: bool
):
    from conda_self.migration_inventory import inspect_migration_inventory

    distribution(tmp_path, "external", entry_points=entry_points)
    records = [record("python", version="3.13")]

    if is_plugin:
        with pytest.raises(CondaValueError, match="externally installed conda plugin"):
            inspect_migration_inventory(tmp_path, records)
    else:
        inventory = inspect_migration_inventory(tmp_path, records)
        assert inventory.external_packages == ("external==1.0",)


def test_entry_point_names_are_case_sensitive(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    distribution(
        tmp_path,
        "external",
        entry_points="[console_scripts]\nfoo = never_import_this:main\n"
        "Foo = never_import_this:other\n",
    )

    inventory = inspect_migration_inventory(
        tmp_path, [record("python", version="3.13")]
    )

    assert inventory.external_packages == ("external==1.0",)


def test_rejects_unrecorded_entry_points_in_owned_metadata(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(
        tmp_path, "owned", entry_points="[conda]\nplugin = never_import_this:plugin\n"
    )
    with pytest.raises(CondaValueError, match="entry-point metadata"):
        inspect_migration_inventory(tmp_path, [record("owned-package", files[0])])


@pytest.mark.parametrize(
    "contents",
    [
        "Version: 1.0\n",
        "Name: broken\n",
        "Name: broken\nVersion: 1.0\nRequires-Dist: invalid @@ requirement\n",
    ],
)
def test_rejects_incomplete_or_invalid_external_metadata(tmp_path: Path, contents: str):
    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(tmp_path, "broken")
    (tmp_path / files[0]).write_text(contents)
    with pytest.raises(CondaValueError, match="metadata"):
        inspect_migration_inventory(tmp_path, [record("python", version="3.13")])


def test_rejects_unreadable_entry_points(tmp_path: Path, monkeypatch):
    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(tmp_path, "broken", entry_points="[conda]\nx = x:plugin\n")
    entry_points = tmp_path / files[1]
    read_text = Path.read_text

    def unreadable(path, *args, **kwargs):
        if path == entry_points:
            raise PermissionError("Cannot read metadata")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)
    with pytest.raises(CondaValueError, match="metadata") as error:
        inspect_migration_inventory(tmp_path, [record("python", version="3.13")])
    assert str(tmp_path) not in str(error.value)


def test_reports_python_files_without_distribution_metadata(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    site = tmp_path / SITE_PACKAGES
    (site / "untracked_package").mkdir(parents=True)
    (site / "untracked_package" / "__init__.py").write_text("value = 1\n")
    inventory = inspect_migration_inventory(
        tmp_path, [record("python", version="3.13")]
    )

    assert inventory.external_packages == ("untracked Python files",)


def test_owned_python_files_do_not_count_as_external(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    filename = f"{SITE_PACKAGES}/owned_module.py"
    (tmp_path / filename).parent.mkdir(parents=True)
    (tmp_path / filename).write_text("value = 1\n")
    inventory = inspect_migration_inventory(
        tmp_path, [record("python", version="3.13"), record("owned", filename)]
    )

    assert inventory.external_packages == ()


def test_rejects_malformed_entry_points(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    distribution(tmp_path, "broken", entry_points="not an entry points file\n")
    with pytest.raises(CondaValueError, match="metadata"):
        inspect_migration_inventory(tmp_path, [record("python", version="3.13")])


def test_uses_site_packages_parent_of_owned_modules(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    filename = "custom/site-packages/owned_module.py"
    (tmp_path / filename).parent.mkdir(parents=True)
    (tmp_path / filename).write_text("value = 1\n")
    distribution(tmp_path, "external", parent="custom/site-packages")

    inventory = inspect_migration_inventory(tmp_path, [record("owned", filename)])

    assert inventory.external_packages == ("external==1.0",)


def test_rejects_missing_owned_metadata(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    filename = f"{SITE_PACKAGES}/missing-1.0.dist-info/entry_points.txt"
    with pytest.raises(CondaValueError, match="metadata"):
        inspect_migration_inventory(tmp_path, [record("missing", filename)])


def test_wheel_record_identifies_external_module_files(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(tmp_path, "external")
    metadata = (tmp_path / files[0]).parent
    (metadata.parent / "external.py").write_text("value = 1\n")
    (metadata / "RECORD").write_text(
        "external.py,,\nexternal-1.0.dist-info/METADATA,,\n"
    )
    inventory = inspect_migration_inventory(
        tmp_path, [record("python", version="3.13")]
    )

    assert inventory.external_packages == ("external==1.0",)


@pytest.mark.parametrize("record_contents", ["external.py,,invalid-size\n", "\n"])
def test_rejects_invalid_external_manifest(tmp_path: Path, record_contents: str):
    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(tmp_path, "external")
    manifest = (tmp_path / files[0]).parent / "RECORD"
    manifest.write_text(record_contents)

    with pytest.raises(CondaValueError, match="metadata"):
        inspect_migration_inventory(tmp_path, [record("python", version="3.13")])


def test_external_wheel_without_manifest_retains_untracked_files(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(tmp_path, "external")
    metadata = (tmp_path / files[0]).parent
    (metadata / "RECORD").unlink()
    (metadata.parent / "external.py").write_text("value = 1\n")

    inventory = inspect_migration_inventory(
        tmp_path, [record("python", version="3.13")]
    )

    assert inventory.external_packages == ("external==1.0", "untracked Python files")


def test_external_wheel_manifest_supports_sha512(tmp_path: Path):
    from base64 import urlsafe_b64encode
    from hashlib import sha512

    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(tmp_path, "external")
    metadata = (tmp_path / files[0]).parent
    content = b"value = 1\n"
    (metadata.parent / "external.py").write_bytes(content)
    digest = urlsafe_b64encode(sha512(content).digest()).decode().rstrip("=")
    (metadata / "RECORD").write_text(f"external.py,sha512={digest},{len(content)}\n")

    inventory = inspect_migration_inventory(
        tmp_path, [record("python", version="3.13")]
    )

    assert inventory.external_packages == ("external==1.0",)


def test_legacy_egg_optional_requirement_with_quoted_marker(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(tmp_path, "external", directory="external-1.0.egg-info")
    metadata = (tmp_path / files[0]).parent
    (metadata / "requires.txt").write_text('[opt:python_version >= "3"]\nconda\n')

    inventory = inspect_migration_inventory(
        tmp_path, [record("python", version="3.13"), record("conda")]
    )

    assert inventory.external_packages == ("external==1.0",)
    assert inventory.external_required_names == frozenset({"conda"})


@pytest.mark.parametrize(
    "name", ["ordinary>=1", "ordinary[extra]", "ordinary @ https://example.test/pkg"]
)
def test_rejects_requirements_used_as_distribution_names(tmp_path: Path, name: str):
    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(tmp_path, "broken")
    (tmp_path / files[0]).write_text(f"Name: {name}\nVersion: 1.0\n")
    with pytest.raises(CondaValueError, match="metadata"):
        inspect_migration_inventory(tmp_path, [record("python", version="3.13")])


@pytest.mark.parametrize("anchor", ["entry_points.txt", "RECORD"])
def test_rejects_missing_owned_metadata_anchor(tmp_path: Path, anchor: str):
    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(tmp_path, "owned")
    missing = str(Path(files[0]).parent / anchor)
    (tmp_path / missing).unlink(missing_ok=True)
    with pytest.raises(CondaValueError, match="metadata"):
        inspect_migration_inventory(tmp_path, [record("owned", *files, missing)])


@pytest.mark.parametrize("anchor", ["entry_points.txt", "RECORD"])
def test_rejects_unreadable_owned_metadata_anchor(
    tmp_path: Path, monkeypatch, anchor: str
):
    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(tmp_path, "owned")
    relative = Path(files[0]).parent / anchor
    target = tmp_path / relative
    target.write_text("")
    read_text = Path.read_text

    def unreadable(path, *args, **kwargs):
        if path == target:
            raise PermissionError("Cannot read metadata")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)
    with pytest.raises(CondaValueError, match="metadata"):
        inspect_migration_inventory(tmp_path, [record("owned", *files, str(relative))])


@pytest.mark.parametrize("suffix", [".pth", ".egg-link"])
@pytest.mark.parametrize("wheel_owned", [False, True])
def test_rejects_external_import_redirects(
    tmp_path: Path, suffix: str, wheel_owned: bool
):
    from conda_self.migration_inventory import inspect_migration_inventory

    files = distribution(tmp_path, "external")
    metadata = (tmp_path / files[0]).parent
    redirect = metadata.parent / f"external{suffix}"
    redirect.write_text("../external-source\n")
    if wheel_owned:
        (metadata / "RECORD").write_text(f"{redirect.name},,\n")

    with pytest.raises(CondaValueError, match="import"):
        inspect_migration_inventory(tmp_path, [record("python", version="3.13")])


def test_accepts_conda_owned_pth_file(tmp_path: Path):
    from conda_self.migration_inventory import inspect_migration_inventory

    filename = f"{SITE_PACKAGES}/owned.pth"
    (tmp_path / filename).parent.mkdir(parents=True)
    (tmp_path / filename).write_text("owned_module\n")
    inventory = inspect_migration_inventory(tmp_path, [record("owned", filename)])

    assert inventory.external_packages == ()
