from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(
    sys.platform == "win32" or shutil.which("bash") is None,
    reason="VHS setup requires a Unix bash shell",
)
@pytest.mark.parametrize("failure", ["download", "installer"])
def test_demo_setup_stops_on_bootstrap_failure(tmp_path: Path, failure: str) -> None:
    script = Path(__file__).parents[1] / "demos" / "_setup.sh"
    result = subprocess.run(
        [
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            """
            curl() { test "$FAILURE" != download; }
            bash() { return 1; }
            rm() {
                case "$*" in
                    *"/tmp/miniforge-demo"*) exit 99 ;;
                    *) command rm "$@" ;;
                esac
            }
            source "$1"
            printf 'UNSAFE: recording continued\\n'
            """,
            "test-demo-setup",
            str(script),
        ],
        env={**os.environ, "TMPDIR": str(tmp_path), "FAILURE": failure},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "recording continued" not in result.stdout
    assert "Demo setup failed" in result.stderr
    assert not list(tmp_path.iterdir())
