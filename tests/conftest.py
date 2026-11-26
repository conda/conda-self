from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from conda.core.package_cache_data import PackageCacheData
from conda.core.prefix_data import PrefixData
from conda.plugins.hookspec import CondaSpecs
from conda.plugins.manager import CondaPluginManager

if TYPE_CHECKING:
    from collections.abc import Iterator

    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture

pytest_plugins = (
    "conda.testing",
    "conda.testing.fixtures",
)


@pytest.fixture
def conda_channel() -> str:
    return os.environ.get("TEST_CONDA_CHANNEL", "conda-forge")


@pytest.fixture
def python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


@pytest.fixture
def plugin_manager(mocker) -> CondaPluginManager:
    pm = CondaPluginManager()
    pm.add_hookspecs(CondaSpecs)
    mocker.patch("conda.plugins.manager.get_plugin_manager", return_value=pm)
    return pm


@pytest.fixture(scope="session")
def _session_env(
    session_tmp_env: TmpEnvFixture,
    session_conda_cli: CondaCLIFixture,
) -> Iterator[Path]:
    """Session-scoped env with the running conda and current conda-self checkout.

    Created once per test run. Tests get clones via ``base_env``.
    """
    channel = os.environ.get("TEST_CONDA_CHANNEL", "conda-forge")
    python_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    conda_record = PrefixData(sys.prefix, interoperability=False).get("conda")
    conda_archive = PackageCacheData.get_entry_to_link(
        conda_record
    ).package_tarball_full_path
    package_dir = session_tmp_env.get_path(name="conda-self-package")
    session_conda_cli(
        "pypi",
        "convert",
        "--editable",
        str(Path(__file__).resolve().parents[1]),
        "--output-folder",
        package_dir,
    )
    self_archive = next(package_dir.glob("conda-self-*.conda"))

    with session_tmp_env(
        "conda >=26.10.0",
        "coverage >=7.13",
        f"python={python_ver}",
        f"--channel={channel}",
    ) as prefix:
        session_conda_cli(
            "install",
            "--prefix",
            prefix,
            "--yes",
            "--no-deps",
            conda_archive,
            self_archive,
        )
        yield prefix


@pytest.fixture
def base_env(
    _session_env: Path,
    tmp_path: Path,
    conda_cli: CondaCLIFixture,
) -> Path:
    """Function-scoped clone of the session env (fast — hardlinks, no solving)."""
    conda_cli(
        "create",
        f"--prefix={tmp_path / 'env'}",
        f"--clone={_session_env}",
        "--yes",
        "--quiet",
    )
    return tmp_path / "env"
