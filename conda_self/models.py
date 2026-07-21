"""Public models for conda-self installer adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@dataclass(frozen=True)
class UninstallRequest:
    """Arguments passed to the uninstall callback."""

    prefix: Path
    dry_run: bool = False
    yes: bool = False
    json: bool = False
    quiet: bool = False


@dataclass(frozen=True)
class LauncherUpdateRequest:
    """Arguments passed to the launcher update callback."""

    prefix: Path
    force_reinstall: bool = False
    dry_run: bool = False
    yes: bool = False
    json: bool = False
    quiet: bool = False


@dataclass(frozen=True)
class CondaSelfAdapter:
    """Installer callbacks for uninstalling a prefix or updating its launcher."""

    name: str
    uninstall: Callable[[UninstallRequest], int] | None = None
    update_launcher: Callable[[LauncherUpdateRequest], int] | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Adapter name must not be empty")
        if self.uninstall is None and self.update_launcher is None:
            raise ValueError("Adapter must implement at least one operation")
