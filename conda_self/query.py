"""Queries for package dependency information."""

from __future__ import annotations

import sys

from conda.base.context import context
from conda.core.prefix_data import PrefixData
from conda.models.prefix_graph import PrefixGraph

from .constants import PERMANENT_PACKAGES, SELF_PERMANENT_PACKAGES_SETTING


def permanent_dependencies(add_plugins: bool = False) -> set[str]:
    """Get the full list of dependencies for all the permanent packages."""
    # In some dev environments, conda-self is installed as a PyPI package
    # and does not have its conda-meta/conda-self-*.json entry, which makes it
    # invisible to PrefixData()... unless we enable interoperability.
    installed = list(PrefixData(sys.prefix, interoperability=True).iter_records())
    prefix_graph = PrefixGraph(installed)

    protect = {
        *PERMANENT_PACKAGES,
        *getattr(context.plugins, SELF_PERMANENT_PACKAGES_SETTING),
    }

    if add_plugins:
        protect.update(
            record.name
            for record in installed
            if context.plugin_manager.is_conda_plugin_package(record, prefix=sys.prefix)
        )

    packages = set()
    for record in installed:
        if record.name in protect:
            packages.add(record.name)
            packages.update(
                parent.name for parent in prefix_graph.all_ancestors(record)
            )
    return packages
