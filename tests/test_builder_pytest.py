import sys
import shutil
from pathlib import Path
import pytest
from q2sfx.builder import Q2SFXBuilder

TEST_APP = Path("tests/test_app.py")  # Путь к тестовому скрипту
OUTPUT_DIR = Path("tests/dist_sfx")  # Папка для финального SFX


@pytest.fixture(scope="module")
def builder():
    b = Q2SFXBuilder(str(TEST_APP), console=True, output_dir=str(OUTPUT_DIR))
    yield b
    # Cleanup after all tests
    b.cleanup()
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)


def test_check_go(builder):
    """Check that Go is installed."""
    builder.check_go()  # Должно пройти без ошибок


def test_build_sfx(builder):
    """Full build SFX workflow."""
    output_file = OUTPUT_DIR / "test_app_setup.exe"
    final_path = builder.build_sfx(str(output_file))
    assert Path(final_path).exists(), "SFX file was not created"
    assert Path(final_path).is_file(), "SFX path is not a file"
