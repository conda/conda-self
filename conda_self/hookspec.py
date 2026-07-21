"""Private Pluggy hooks owned by conda-self."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pluggy

PROJECT_NAME = "conda_self"
ENTRY_POINT_GROUP = "conda_self"

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from .models import CondaSelfAdapter


hookspec = pluggy.HookspecMarker(PROJECT_NAME)
hookimpl = pluggy.HookimplMarker(PROJECT_NAME)


@hookspec
def conda_self_adapters(prefix: Path) -> Iterable[CondaSelfAdapter]:
    """Yield an adapter for ``prefix`` when this provider recognizes it."""
    raise NotImplementedError
