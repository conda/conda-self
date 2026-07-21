from __future__ import annotations

from typing import TYPE_CHECKING

from conda.exceptions import CondaError

if TYPE_CHECKING:
    from pathlib import Path


def _plural(word: str, count: int) -> str:
    return word if count == 1 else f"{word}s"


class NotAPluginError(CondaError):
    def __init__(self, specs: list[str]):
        names = ", ".join(specs)
        if len(specs) == 1:
            msg = f"The requested package is not a plugin: {names}"
        else:
            msg = f"The requested packages are not plugins: {names}"
        super().__init__(msg)


class PluginRemoveError(CondaError):
    def __init__(self, specs: list[str]):
        names = ", ".join(specs)
        noun = _plural("package", len(specs))
        super().__init__(f"{noun.capitalize()} can not be removed: {names}")


class NoDistInfoDirFound(CondaError):
    def __init__(self, package_name: str, path: str | Path):
        super().__init__(
            f"No *.dist-info directories found for '{package_name}' in '{path}'."
        )


class InstallerAdapterError(CondaError):
    """Base class for installer adapter errors."""


class InvalidInstallerAdapterError(InstallerAdapterError):
    def __init__(self, adapter: object):
        super().__init__(
            "conda_self_adapters() must yield CondaSelfAdapter objects, "
            f"got {adapter!r}"
        )


class MultipleInstallerAdaptersError(InstallerAdapterError):
    def __init__(self, prefix: Path, names: list[str]):
        super().__init__(
            f"Multiple installer adapters claim '{prefix}': {', '.join(names)}"
        )


class InstallerOperationUnsupportedError(InstallerAdapterError):
    def __init__(self, operation: str, prefix: Path):
        super().__init__(
            f"Cannot {operation} the conda installation at '{prefix}'. "
            "Use the installer or package manager that installed it."
        )
