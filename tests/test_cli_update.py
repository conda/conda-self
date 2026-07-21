from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from conda.exceptions import CondaValueError

from conda_self.models import CondaSelfAdapter
from conda_self.testing import conda_cli_subprocess

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture
    from pytest import MonkeyPatch


def test_help(conda_cli: CondaCLIFixture):
    out, err, exc = conda_cli("self", "update", "--help", raises=SystemExit)
    assert exc.value.code == 0


def test_update_plugin_invalid(conda_cli: CondaCLIFixture):
    conda_cli("self", "update", "--plugin", "conda-fake-solver", raises=CondaValueError)


def test_bare_update_dispatches_to_installer_adapter(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    requests = []

    def update_launcher(request) -> int:
        requests.append(request)
        return 0

    adapter = CondaSelfAdapter(name="test", update_launcher=update_launcher)
    monkeypatch.setattr("conda_self.registry.get_adapter", lambda prefix: adapter)

    conda_cli("self", "update", "--force-reinstall", "--dry-run", "--yes", "--quiet")

    assert len(requests) == 1
    request = requests[0]
    assert request.prefix.is_absolute()
    assert request.force_reinstall is True
    assert request.dry_run is True
    assert request.yes is True
    assert request.quiet is True


@pytest.mark.parametrize(
    "extra_args,expected",
    (
        pytest.param((), "conda (installed:", id="conda"),
        pytest.param(
            ("--plugin", "conda-libmamba-solver"),
            "conda-libmamba-solver (installed:",
            id="plugin",
        ),
        pytest.param(("--all",), "conda (installed:", id="all"),
        pytest.param(
            ("--all", "--force-reinstall"),
            "conda (installed:",
            id="all+force-reinstall",
        ),
    ),
)
def test_update(
    extra_args: tuple[str, ...],
    expected: str,
    monkeypatch: MonkeyPatch,
    base_env: Path,
    conda_channel: str,
):
    monkeypatch.setenv("CONDA_CHANNELS", conda_channel)

    result = conda_cli_subprocess(
        base_env,
        "self",
        "update",
        *extra_args,
        "--dry-run",
        "--yes",
        capture_output=True,
        text=True,
    )
    assert "Updating" in result.stdout
    assert expected in result.stdout
