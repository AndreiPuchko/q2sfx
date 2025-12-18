import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def tool_exists(cmd):
    return shutil.which(cmd) is not None


@pytest.mark.integration
@pytest.mark.skipif(
    not tool_exists("go"),
    reason="Go is not installed",
)
@pytest.mark.skipif(
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode
    != 0,
    reason="PyInstaller is not available",
)
def test_build_real_sfx(tmp_path):
    """
    Full integration test:
    - runs q2sfx CLI
    - builds PyInstaller payload
    - builds Go SFX
    - verifies resulting executable
    """
    app = Path("tests/test_app.py").resolve()
    assert app.exists(), "Test app does not exist"

    output = tmp_path / "test_app_setup.exe"

    cmd = [
        sys.executable,
        "-m",
        "q2sfx",
        str(app),
        "--console",
        "-o",
        str(output),
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Debug output if failed
    if result.returncode != 0:
        print("STDOUT:\n", result.stdout)
        print("STDERR:\n", result.stderr)

    assert result.returncode == 0
    assert output.exists()
    assert output.stat().st_size > 0
