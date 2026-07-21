from __future__ import annotations

from typing import TYPE_CHECKING

import pluggy
import pytest

from conda_self.exceptions import (
    InvalidInstallerAdapterError,
    MultipleInstallerAdaptersError,
)
from conda_self.hookspec import ENTRY_POINT_GROUP, hookimpl
from conda_self.models import CondaSelfAdapter
from conda_self.registry import AdapterRegistry

if TYPE_CHECKING:
    from pathlib import Path


def uninstall(_request) -> int:
    return 0


def test_registry_is_private_pluggy_manager() -> None:
    registry = AdapterRegistry()

    assert isinstance(registry, pluggy.PluginManager)
    assert hasattr(registry.hook, "conda_self_adapters")


def test_discover_uses_private_entry_point_group(monkeypatch) -> None:
    groups: list[str] = []

    def load_entry_points(self, group: str) -> int:
        groups.append(group)
        return 0

    monkeypatch.setattr(
        pluggy.PluginManager,
        "load_setuptools_entrypoints",
        load_entry_points,
    )

    AdapterRegistry.discover()

    assert groups == [ENTRY_POINT_GROUP]


def test_registry_collects_adapter_for_claimed_prefix(tmp_path: Path) -> None:
    claimed = tmp_path / "claimed"

    class Provider:
        @hookimpl
        def conda_self_adapters(self, prefix: Path):
            if prefix == claimed:
                yield CondaSelfAdapter(name="test", uninstall=uninstall)

    registry = AdapterRegistry()
    registry.register(Provider(), name="provider")

    assert registry.applicable(tmp_path) is None
    adapter = registry.applicable(claimed)
    assert adapter is not None
    assert adapter.name == "test"


def test_registry_rejects_invalid_adapter(tmp_path: Path) -> None:
    class Provider:
        @hookimpl
        def conda_self_adapters(self, prefix: Path):
            yield "not-an-adapter"

    registry = AdapterRegistry()
    registry.register(Provider(), name="provider")

    with pytest.raises(InvalidInstallerAdapterError):
        registry.applicable(tmp_path)


def test_registry_rejects_multiple_applicable_adapters(tmp_path: Path) -> None:
    class FirstProvider:
        @hookimpl
        def conda_self_adapters(self, prefix: Path):
            yield CondaSelfAdapter(name="first", uninstall=uninstall)

    class SecondProvider:
        @hookimpl
        def conda_self_adapters(self, prefix: Path):
            yield CondaSelfAdapter(name="second", uninstall=uninstall)

    registry = AdapterRegistry()
    registry.register(FirstProvider(), name="first-provider")
    registry.register(SecondProvider(), name="second-provider")

    with pytest.raises(MultipleInstallerAdaptersError, match="first, second"):
        registry.applicable(tmp_path)


def test_adapter_requires_name_and_operation() -> None:
    with pytest.raises(ValueError, match="name"):
        CondaSelfAdapter(name="", uninstall=uninstall)
    with pytest.raises(ValueError, match="operation"):
        CondaSelfAdapter(name="test")
