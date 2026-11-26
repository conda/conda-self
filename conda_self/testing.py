from __future__ import annotations

import os
from pathlib import Path
from subprocess import run
from typing import TYPE_CHECKING

from conda.core.prefix_data import PrefixData

if TYPE_CHECKING:
    from subprocess import CompletedProcess

    from conda.models.match_spec import MatchSpec
    from conda.models.records import PackageRecord


def conda_cli_subprocess(prefix: str | Path, *args, **kwargs) -> CompletedProcess:
    prefix = Path(prefix)
    if os.name == "nt":
        python = prefix / "python.exe"
    else:
        python = prefix / "bin" / "python"

    # Use the subprocess's own conda: the runner's PYTHONPATH breaks DLL loading.
    env = dict(kwargs.pop("env", None) or os.environ)
    for name in ("PYTHONPATH", "PYTHONHOME"):
        env.pop(name, None)

    return run(
        [python, "-m", "conda", *args],
        check=kwargs.pop("check", True),
        env=env,
        **kwargs,
    )


def is_installed(prefix: str | Path, package: PackageRecord | MatchSpec | str):
    PrefixData._cache_.clear()
    return bool(list(PrefixData(prefix).query(package)))
