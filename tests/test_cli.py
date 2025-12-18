import subprocess
import sys


def run_cli(args):
    """
    Helper to run q2sfx CLI in a subprocess.
    """
    cmd = [sys.executable, "-m", "q2sfx"] + args
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_version_flag():
    result = run_cli(["--version"])

    assert result.returncode == 0
    assert result.stdout.startswith("q2sfx ")
    assert result.stderr == ""


def test_help_flag():
    result = run_cli(["--help"])

    assert result.returncode == 0
    assert "Build a self-extracting executable" in result.stdout
    assert "usage:" in result.stdout.lower()


def test_missing_app_argument():
    result = run_cli([])

    # argparse exits with code 2 on error
    assert result.returncode == 2
    assert "usage:" in result.stderr.lower()
