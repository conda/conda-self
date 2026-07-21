"""Discovery for distribution-owned conda-self adapters."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pluggy

from .exceptions import InvalidInstallerAdapterError, MultipleInstallerAdaptersError
from .hookspec import ENTRY_POINT_GROUP, PROJECT_NAME
from .models import CondaSelfAdapter

if TYPE_CHECKING:
    from collections.abc import Iterable


class AdapterRegistry(pluggy.PluginManager):
    """Pluggy manager for the private conda-self adapter group."""

    def __init__(self) -> None:
        super().__init__(PROJECT_NAME)
        from . import hookspec as conda_self_hookspec

        self.add_hookspecs(conda_self_hookspec)

    @classmethod
    def discover(cls) -> AdapterRegistry:
        """Load adapters from the private conda-self entry-point group."""
        registry = cls()
        registry.load_setuptools_entrypoints(ENTRY_POINT_GROUP)
        return registry

    def applicable(self, prefix: Path) -> CondaSelfAdapter | None:
        """Return the one adapter that claims ``prefix``, if any."""
        adapters = list(self._collect(prefix))
        if len(adapters) > 1:
            raise MultipleInstallerAdaptersError(
                prefix=prefix,
                names=sorted(adapter.name for adapter in adapters),
            )
        return adapters[0] if adapters else None

    def _collect(self, prefix: Path) -> Iterable[CondaSelfAdapter]:
        for result in self.hook.conda_self_adapters(prefix=prefix):
            for adapter in result or ():
                if not isinstance(adapter, CondaSelfAdapter):
                    raise InvalidInstallerAdapterError(adapter)
                yield adapter


def get_adapter(prefix: str | Path) -> CondaSelfAdapter | None:
    """Discover the installer adapter for ``prefix``."""
    return AdapterRegistry.discover().applicable(Path(prefix))
