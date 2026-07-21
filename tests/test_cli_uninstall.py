from __future__ import annotations

from typing import TYPE_CHECKING

from conda_self.exceptions import InstallerOperationUnsupportedError
from conda_self.models import CondaSelfAdapter

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture
    from pytest import MonkeyPatch


def test_help(conda_cli: CondaCLIFixture) -> None:
    _out, _err, exc = conda_cli("self", "uninstall", "--help", raises=SystemExit)
    assert exc.value.code == 0


def test_uninstall_requires_adapter(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("conda_self.registry.get_adapter", lambda prefix: None)

    conda_cli("self", "uninstall", "--yes", raises=InstallerOperationUnsupportedError)


def test_uninstall_dispatches_to_adapter(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    requests = []

    def uninstall(request) -> int:
        requests.append(request)
        return 0

    adapter = CondaSelfAdapter(name="test", uninstall=uninstall)
    monkeypatch.setattr("conda_self.registry.get_adapter", lambda prefix: adapter)

    conda_cli("self", "uninstall", "--yes", "--dry-run", "--quiet")

    assert len(requests) == 1
    request = requests[0]
    assert request.prefix.is_absolute()
    assert request.dry_run is True
    assert request.yes is True
    assert request.quiet is True


def test_uninstall_requires_adapter_capability(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    adapter = CondaSelfAdapter(name="test", update_launcher=lambda request: 0)
    monkeypatch.setattr("conda_self.registry.get_adapter", lambda prefix: adapter)

    conda_cli("self", "uninstall", "--yes", raises=InstallerOperationUnsupportedError)
