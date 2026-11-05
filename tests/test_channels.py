from conda.models.channel import Channel
from conda.models.records import PrefixRecord


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

from conda_self.channels import ChannelChange, find_channel_changes


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
    installed= [installed_package("r-base", "pkgs/main")]
    planned= [{"name": "r-base", "channel": "pkgs/r"}]

    assert find_channel_changes(installed, planned) == []


def test_channel_url_and_channel_name_are_equivalent() -> None:
    installed = [installed_package("conda", "https://conda.anaconda.org/conda-forge")]
    planned=[ {"name": "conda", "channel": "conda-forge"}]
    assert find_channel_changes(installed, planned) == []


def test_new_package_is_ignored() -> None:
    installed = [installed_package("conda", "https://conda.anaconda.org/conda-forge")]
    planned= [{"name": "new-package", "channel": "pkgs/main"}]
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