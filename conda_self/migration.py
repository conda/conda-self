"""Plan an exact-version separation of base and user packages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from conda import CondaError
from conda.exceptions import CondaValueError
from conda.models.match_spec import MatchSpec
from conda.models.prefix_graph import PrefixGraph

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

    from conda.models.records import PackageRecord, PrefixRecord


@dataclass(frozen=True)
class MigrationPlan:
    base_names: frozenset[str]
    default_names: frozenset[str]
    requested_specs: tuple[MatchSpec, ...]
    default_excluded_user_names: frozenset[str]
    removed_from_both_names: frozenset[str]


def plan_migration(
    records: Iterable[PrefixRecord],
    *,
    plugin_names: Collection[str],
    requested_specs: Mapping[str, MatchSpec],
    base_roots: Collection[str],
    virtual_records: Iterable[PackageRecord] = (),
    preserve_dependencies: bool = False,
) -> MigrationPlan:
    """Select closed package sets from validated installed records.

    Management packages and their reverse dependents stay out of default.
    Their exclusive dependencies are retained only in base, unless requested
    independently or preserve_dependencies is set for external code. Missing
    history is filled from top-level user packages. No records are modified
    and no solver is used.
    """
    records = tuple(records)
    virtual_records = tuple(virtual_records)
    for group in (records, virtual_records):
        seen = set()
        for record in group:
            if record.name in seen:
                raise CondaValueError(f"Duplicate installed package: {record.name}")
            seen.add(record.name)

    installed = {record.name: record for record in records}
    available = {record.name: record for record in virtual_records}
    available.update(installed)
    for name, record in installed.items():
        for required, values in ((True, record.depends), (False, record.constrains)):
            for value in values:
                try:
                    spec = MatchSpec(value)
                except (CondaError, ValueError, TypeError) as exc:
                    raise CondaValueError(
                        f"Invalid dependency metadata for {name}"
                    ) from exc
                if not spec.get_exact_value("name"):
                    raise CondaValueError(
                        f"Dependency without an exact package name for {name}"
                    )
                dependency = available.get(spec.name)
                if dependency is None and not required:
                    continue
                if dependency is None or not spec.match(dependency):
                    kind = "dependency" if required else "constraint"
                    raise CondaValueError(
                        f"Unsatisfied installed {kind} for {name}: {spec.name}"
                    )

    graph = PrefixGraph(records)
    # Compute each package's dependency closure once, then use these sets for every
    # selection below, including reverse dependents and requested-history roots.
    dependencies = {
        record.name: {record.name}
        | {parent.name for parent in graph.all_ancestors(record)}
        for record in records
    }
    names = frozenset(installed)
    management = names.intersection({"conda", "conda-self", *plugin_names})
    management_dependencies = {
        dependency for name in management for dependency in dependencies[name]
    }
    base = frozenset(
        dependency
        for name in management | names.intersection(base_roots)
        for dependency in dependencies[name]
    )
    excluded = frozenset(
        name for name, ancestors in dependencies.items() if ancestors & management
    )
    user_names = names - management_dependencies - excluded
    original_names = names.intersection(requested_specs) - excluded
    default = (
        names - excluded
        if preserve_dependencies
        else frozenset(
            dependency
            for name in user_names | original_names
            for dependency in dependencies[name]
        )
    )

    # Fill missing history from top-level user packages. Explicit requests stay
    # independent, and an otherwise unrequested cycle keeps its first name.
    inferred = set(user_names) - {
        dependency for name in original_names for dependency in dependencies[name]
    }
    for name in sorted(inferred):
        if name in inferred:
            inferred.difference_update(dependencies[name] - {name})
    roots = original_names | inferred

    # An old request may no longer match the installed version. Preserve its
    # independent-root status without reintroducing the obsolete constraint.
    requested = []
    for name in sorted(roots):
        spec = requested_specs.get(name, MatchSpec(name))
        requested.append(spec if spec.match(installed[name]) else MatchSpec(name))

    return MigrationPlan(
        base_names=base,
        default_names=default,
        requested_specs=tuple(requested),
        default_excluded_user_names=excluded - management,
        removed_from_both_names=names - base - default,
    )
