from __future__ import annotations

from conda.exceptions import CondaError


class PluginRemoveError(CondaError):
    def __init__(self, specs: list[str]):
        names = ", ".join(specs)
        noun = "package" if len(specs) == 1 else "packages"
        super().__init__(
            f"conda-self protects the requested {noun} from removal: {names}\n"
            "Pass --force to bypass this check. Conda's own transaction checks "
            "still apply."
        )
