import os
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Iterator

import pytest
from conda.exceptions import CondaValueError
from conda.models.channel import Channel
from conda.models.records import PrefixRecord

from conda_self.channels import (
    ChannelChange,
    check_solved_channel_changes,
    find_channel_changes,
)


def installed_package(name: str, channel: str) -> PrefixRecord:
    return PrefixRecord(
        name=name,
        version="1.0",
        build="0",
        build_number=0,
        channel=Channel(channel),
        subdir="osx-arm64",
        fn=f"{name}-1.0-0.conda",
    )


def test_detects_channel_change() -> None:
    installed = [installed_package("conda", "conda-forge")]
    planned = [{"name": "conda", "channel": "pkgs/main"}]

    assert find_channel_changes(installed, planned) == [
        ChannelChange(
            name="conda",
            installed_channel="https://conda.anaconda.org/conda-forge",
            planned_channel="pkgs/main",
        )
    ]


def test_moving_within_defaults_is_not_a_change() -> None:
    installed = [installed_package("r-base", "pkgs/main")]
    planned = [{"name": "r-base", "channel": "pkgs/r"}]

    assert find_channel_changes(installed, planned) == []


def test_moving_defaults_to_a_different_host_is_a_change() -> None:
    installed = [installed_package("conda", "https://repo.anaconda.com/pkgs/main")]
    planned = [{"name": "conda", "channel": "https://example.invalid/pkgs/main"}]

    assert find_channel_changes(installed, planned) == [
        ChannelChange(
            name="conda",
            installed_channel="https://repo.anaconda.com/pkgs/main",
            planned_channel="https://example.invalid/pkgs/main",
        )
    ]


def test_channel_url_and_channel_name_are_equivalent() -> None:
    installed = [installed_package("conda", "https://conda.anaconda.org/conda-forge")]
    planned = [{"name": "conda", "channel": "conda-forge"}]
    assert find_channel_changes(installed, planned) == []


def test_new_package_is_ignored() -> None:
    installed = [installed_package("conda", "https://conda.anaconda.org/conda-forge")]
    planned = [{"name": "new-package", "channel": "pkgs/main"}]
    assert find_channel_changes(installed, planned) == []


def test_unknown_installed_channel_is_ignored() -> None:
    installed = [installed_package("conda", "<unknown>")]
    planned = [{"name": "conda", "channel": "pkgs/main"}]
    assert find_channel_changes(installed, planned) == []


def test_only_the_package_that_moves_is_reported() -> None:
    installed = [
        installed_package("conda", "pkgs/main"),
        installed_package("some-plugin", "conda-forge"),
    ]
    planned = [
        {"name": "conda", "channel": "conda-forge"},
        {"name": "some-plugin", "channel": "conda-forge"},
    ]

    assert find_channel_changes(installed, planned) == [
        ChannelChange(
            name="conda",
            installed_channel="https://repo.anaconda.com/pkgs/main",
            planned_channel="conda-forge",
        )
    ]


def moved_package_pair() -> tuple[tuple[PrefixRecord, ...], tuple[PrefixRecord, ...]]:
    """Solved records where conda moves from conda-forge to pkgs/main."""
    return (
        (installed_package("conda", "conda-forge"),),
        (installed_package("conda", "pkgs/main"),),
    )


@contextmanager
def hook_context(
    *, dry_run: bool = False, json: bool = False, always_yes: bool = False
) -> Iterator[None]:
    """Drive gate-relevant context flags via CONDA_* env vars + reset_context.

    Same approach as other tests (e.g. CONDA_CHANNELS): never assign
    ``context.dry_run`` / ``json`` / ``always_yes`` directly — that leaves
    instance attributes which shadow later CLI parsing in other tests.
    """
    from conda.base.context import reset_context

    env_flags = {
        "CONDA_DRY_RUN": dry_run,
        "CONDA_JSON": json,
        "CONDA_ALWAYS_YES": always_yes,
    }
    previous = {name: os.environ.get(name) for name in env_flags}
    try:
        for name, enabled in env_flags.items():
            if enabled:
                os.environ[name] = "true"
            else:
                os.environ.pop(name, None)
        reset_context()
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        reset_context()


def set_terminal(monkeypatch: pytest.MonkeyPatch, *, is_tty: bool) -> None:
    import sys

    fake_sys = SimpleNamespace(
        stdin=SimpleNamespace(isatty=lambda: is_tty),
        stderr=sys.stderr,
    )
    monkeypatch.setattr("conda_self.channels.sys", fake_sys)


def test_hook_does_nothing_without_check_env_var(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("CONDA_SELF_CHECK_CHANNEL_CHANGES", raising=False)
    unlink_precs, link_precs = moved_package_pair()

    check_solved_channel_changes("repodata.json", unlink_precs, link_precs)

    assert capsys.readouterr().err == ""


def test_hook_does_nothing_when_nothing_moves(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CONDA_SELF_CHECK_CHANNEL_CHANGES", "1")
    unlink_precs = (installed_package("conda", "conda-forge"),)
    link_precs = (installed_package("conda", "conda-forge"),)

    check_solved_channel_changes("repodata.json", unlink_precs, link_precs)

    assert capsys.readouterr().err == ""


def test_hook_warns_and_proceeds_when_channel_changes_are_allowed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CONDA_SELF_CHECK_CHANNEL_CHANGES", "1")
    monkeypatch.setenv("CONDA_SELF_ALLOW_CHANNEL_CHANGES", "1")
    unlink_precs, link_precs = moved_package_pair()

    check_solved_channel_changes("repodata.json", unlink_precs, link_precs)

    err = capsys.readouterr().err
    assert "Warning" in err
    assert "conda" in err


def test_hook_warns_and_proceeds_on_dry_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CONDA_SELF_CHECK_CHANNEL_CHANGES", "1")
    monkeypatch.delenv("CONDA_SELF_ALLOW_CHANNEL_CHANGES", raising=False)
    unlink_precs, link_precs = moved_package_pair()

    with hook_context(dry_run=True):
        check_solved_channel_changes("repodata.json", unlink_precs, link_precs)

    assert "Warning" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("context_kwargs", "terminal_is_tty"),
    (
        pytest.param({"json": True}, True, id="json-output"),
        pytest.param({"always_yes": True}, True, id="always-yes"),
        pytest.param({}, False, id="no-terminal"),
    ),
)
def test_hook_refuses_channel_changes_without_interactive_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    context_kwargs: dict[str, bool],
    terminal_is_tty: bool,
) -> None:
    monkeypatch.setenv("CONDA_SELF_CHECK_CHANNEL_CHANGES", "1")
    monkeypatch.delenv("CONDA_SELF_ALLOW_CHANNEL_CHANGES", raising=False)
    set_terminal(monkeypatch, is_tty=terminal_is_tty)
    unlink_precs, link_precs = moved_package_pair()

    with hook_context(**context_kwargs):
        with pytest.raises(CondaValueError, match="--allow-channel-changes"):
            check_solved_channel_changes("repodata.json", unlink_precs, link_precs)

    assert "Warning" in capsys.readouterr().err


def test_hook_asks_for_confirmation_on_a_terminal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("CONDA_SELF_CHECK_CHANNEL_CHANGES", "1")
    monkeypatch.delenv("CONDA_SELF_ALLOW_CHANNEL_CHANGES", raising=False)
    set_terminal(monkeypatch, is_tty=True)
    prompts: list[str] = []
    monkeypatch.setattr(
        "conda.reporters.confirm_yn",
        lambda message, **kwargs: prompts.append(message) or True,
    )
    unlink_precs, link_precs = moved_package_pair()

    with hook_context():
        check_solved_channel_changes("repodata.json", unlink_precs, link_precs)

    assert len(prompts) == 1
    assert "Warning" in capsys.readouterr().err
