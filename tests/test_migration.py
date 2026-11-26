from __future__ import annotations

import pytest
from conda.base.context import context
from conda.exceptions import CondaValueError, CyclicalDependencyError
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord, PrefixRecord

from conda_self.migration import plan_migration


def record(name, *depends, version="1.0", build="0", constrains=()):
    return PrefixRecord(
        name=name,
        version=version,
        build=build,
        build_number=0,
        subdir="noarch",
        depends=depends,
        constrains=constrains,
    )


def test_shared_dependencies_stay_at_installed_versions_in_both_environments():
    records = [
        record("conda", "python >=3.13", "conda-runtime"),
        record("conda-self", "conda"),
        record("example-plugin", "plugin-helper", "shared >=2"),
        record("python", version="3.13.4", build="h123_1"),
        record("conda-runtime"),
        record("plugin-helper"),
        record("shared", version="2.1", build="h456_2"),
        record("application", "python >=3.13", "shared >=2"),
    ]
    before = [item.dump() for item in records]

    result = plan_migration(
        records, plugin_names={"example-plugin"}, requested_specs={}, base_roots=()
    )

    assert result.base_names == {
        "conda",
        "conda-self",
        "example-plugin",
        "python",
        "conda-runtime",
        "plugin-helper",
        "shared",
    }
    assert result.default_names == {"application", "python", "shared"}
    assert result.requested_specs == (MatchSpec("application"),)
    assert result.default_excluded_user_names == set()
    assert result.removed_from_both_names == set()
    assert [item.dump() for item in records] == before


def test_independently_requested_management_dependency_remains_in_default():
    result = plan_migration(
        [record("conda", "python"), record("python", version="3.13.4")],
        requested_specs={"python": MatchSpec("python >=3.12,<3.14")},
        plugin_names=(),
        base_roots=(),
    )

    assert result.base_names == {"conda", "python"}
    assert result.default_names == {"python"}
    assert result.requested_specs == (MatchSpec("python >=3.12,<3.14"),)


def test_stale_requested_spec_does_not_repin_installed_dependency():
    result = plan_migration(
        [record("conda", "python"), record("python", version="3.13.4")],
        requested_specs={"python": MatchSpec("python=3.11")},
        plugin_names=(),
        base_roots=(),
    )

    assert result.default_names == {"python"}
    assert result.requested_specs == (MatchSpec("python"),)


def test_missing_history_keeps_nonmanagement_roots():
    result = plan_migration(
        [
            record("conda", "runtime"),
            record("runtime"),
            record("application", "library"),
            record("library"),
        ],
        plugin_names=(),
        requested_specs={},
        base_roots=(),
    )

    assert result.default_names == {"application", "library"}
    assert result.requested_specs == (MatchSpec("application"),)


def test_history_does_not_promote_application_dependencies_to_requested_roots():
    result = plan_migration(
        [
            record("conda", "runtime"),
            record("runtime"),
            record("application", "library"),
            record("library"),
        ],
        requested_specs={"application": MatchSpec("application >=1")},
        plugin_names=(),
        base_roots=(),
    )

    assert result.default_names == {"application", "library"}
    assert result.requested_specs == (MatchSpec("application >=1"),)


def test_missing_application_history_preserves_explicit_library_request():
    result = plan_migration(
        [record("conda"), record("application", "library"), record("library")],
        requested_specs={"library": MatchSpec("library >=1")},
        plugin_names=(),
        base_roots=(),
    )

    assert result.requested_specs == (
        MatchSpec("application"),
        MatchSpec("library >=1"),
    )


@pytest.mark.parametrize(
    "requested, expected",
    [
        ({}, (MatchSpec("cycle-a"),)),
        ({"cycle-b": MatchSpec("cycle-b >=1")}, (MatchSpec("cycle-b >=1"),)),
        (
            {"cycle-a": MatchSpec("cycle-a"), "cycle-b": MatchSpec("cycle-b")},
            (MatchSpec("cycle-a"), MatchSpec("cycle-b")),
        ),
    ],
)
def test_user_dependency_cycles_have_deterministic_requested_roots(requested, expected):
    result = plan_migration(
        [
            record("conda"),
            record("cycle-b", "cycle-a", "library"),
            record("cycle-a", "cycle-b"),
            record("library"),
        ],
        requested_specs=requested,
        plugin_names=(),
        base_roots=(),
    )

    assert result.default_names == {"cycle-a", "cycle-b", "library"}
    assert result.requested_specs == expected


def test_missing_history_keeps_top_level_application_above_dependency_cycle():
    result = plan_migration(
        [
            record("conda"),
            record("cycle-a", "cycle-b"),
            record("cycle-b", "cycle-a"),
            record("z-application", "cycle-a"),
        ],
        plugin_names=(),
        requested_specs={},
        base_roots=(),
    )

    assert result.default_names == {"cycle-a", "cycle-b", "z-application"}
    assert result.requested_specs == (MatchSpec("z-application"),)


@pytest.mark.parametrize("requested", [{}, {"application": MatchSpec("application")}])
def test_external_dependency_retention_does_not_promote_management_libraries(requested):
    result = plan_migration(
        [
            record("conda", "runtime"),
            record("runtime"),
            record("application", "library"),
            record("library"),
        ],
        requested_specs=requested,
        preserve_dependencies=True,
        plugin_names=(),
        base_roots=(),
    )

    assert result.default_names == {"runtime", "application", "library"}
    assert result.requested_specs == (MatchSpec("application"),)


def test_external_dependency_retention_can_have_no_requested_conda_packages():
    result = plan_migration(
        [record("conda", "runtime"), record("runtime")],
        preserve_dependencies=True,
        plugin_names=(),
        requested_specs={},
        base_roots=(),
    )

    assert result.default_names == {"runtime"}
    assert result.requested_specs == ()


def test_management_reverse_dependents_are_omitted_even_when_kept_in_base():
    result = plan_migration(
        [
            record("conda", "runtime"),
            record("runtime"),
            record("plugin", "conda"),
            record("consumer", "plugin"),
            record("consumer-ui", "consumer"),
            record("ordinary"),
        ],
        plugin_names={"plugin"},
        requested_specs={"consumer-ui": MatchSpec("consumer-ui")},
        base_roots={"consumer"},
    )

    assert result.base_names == {"conda", "runtime", "plugin", "consumer"}
    assert result.default_names == {"ordinary"}
    assert result.default_excluded_user_names == {"consumer", "consumer-ui"}
    assert result.removed_from_both_names == {"consumer-ui"}


def test_configured_and_installer_roots_keep_their_dependencies_in_base():
    result = plan_migration(
        [
            record("conda"),
            record("configured", "configured-lib"),
            record("configured-lib"),
            record("installer", "installer-lib"),
            record("installer-lib"),
        ],
        base_roots={"configured", "installer", "not-installed"},
        plugin_names=(),
        requested_specs={},
    )

    assert result.base_names == {
        "conda",
        "configured",
        "configured-lib",
        "installer",
        "installer-lib",
    }
    assert result.default_names == {
        "configured",
        "configured-lib",
        "installer",
        "installer-lib",
    }


def test_exclusive_dependency_cycle_is_removed_from_default():
    result = plan_migration(
        [
            record("conda", "cycle-a"),
            record("cycle-a", "cycle-b"),
            record("cycle-b", "cycle-a"),
            record("application"),
        ],
        plugin_names=(),
        requested_specs={},
        base_roots=(),
    )

    assert result.base_names == {"conda", "cycle-a", "cycle-b"}
    assert result.default_names == {"application"}


def test_disallowed_dependency_cycles_fail_during_planning(monkeypatch):
    monkeypatch.setattr(context, "allow_cycles", False)

    with pytest.raises(CyclicalDependencyError):
        plan_migration(
            [
                record("conda", "cycle-a"),
                record("cycle-a", "cycle-b"),
                record("cycle-b", "cycle-a"),
            ],
            plugin_names=(),
            requested_specs={},
            base_roots=(),
        )


def test_requested_cycle_and_its_dependencies_remain_in_default():
    result = plan_migration(
        [
            record("conda", "cycle-a"),
            record("cycle-a", "cycle-b"),
            record("cycle-b", "cycle-a", "library"),
            record("library"),
        ],
        requested_specs={"cycle-b": MatchSpec("cycle-b >=1")},
        plugin_names=(),
        base_roots=(),
    )

    assert result.default_names == {"cycle-a", "cycle-b", "library"}
    assert result.requested_specs == (MatchSpec("cycle-b >=1"),)


def test_default_can_be_empty():
    result = plan_migration(
        [record("conda", "runtime"), record("runtime")],
        plugin_names=(),
        requested_specs={},
        base_roots=(),
    )

    assert result.default_names == set()
    assert result.requested_specs == ()
    assert result.default_excluded_user_names == set()
    assert result.removed_from_both_names == set()


def test_virtual_dependencies_are_checked_without_becoming_installed_packages():
    result = plan_migration(
        [record("conda", "__platform >=2"), record("application", "__platform >=2")],
        virtual_records=[PackageRecord.virtual_package("__platform", "2.1")],
        plugin_names=(),
        requested_specs={},
        base_roots=(),
    )

    assert result.base_names == {"conda"}
    assert result.default_names == {"application"}


@pytest.mark.parametrize(
    "records, virtual",
    [
        ([record("conda", "missing")], ()),
        ([record("conda", "library >=2"), record("library")], ()),
        ([record("conda", "library 1.0 missing-build"), record("library")], ()),
        ([record("conda", "__platform >=2")], ()),
        (
            [record("conda", "__platform >=2")],
            (PackageRecord.virtual_package("__platform", "1.0"),),
        ),
        ([record("conda", "library >=<1"), record("library")], ()),
        ([record("conda", "*")], ()),
        ([record("conda"), record("conda", version="2.0")], ()),
        (
            [record("conda")],
            (
                PackageRecord.virtual_package("__platform", "1.0"),
                PackageRecord.virtual_package("__platform", "2.0"),
            ),
        ),
    ],
)
def test_invalid_source_records_are_rejected(records, virtual):
    with pytest.raises(CondaValueError):
        plan_migration(
            records,
            virtual_records=virtual,
            plugin_names=(),
            requested_specs={},
            base_roots=(),
        )


def test_optional_constraints_do_not_install_absent_packages():
    result = plan_migration(
        [record("conda"), record("application", constrains=("absent >=2",))],
        plugin_names=(),
        requested_specs={},
        base_roots=(),
    )

    assert result.default_names == {"application"}


def test_conflicting_constraint_in_retained_packages_is_rejected():
    with pytest.raises(CondaValueError):
        plan_migration(
            [
                record("conda"),
                record("application", constrains=("library >=2",)),
                record("library"),
            ],
            plugin_names=(),
            requested_specs={},
            base_roots=(),
        )
