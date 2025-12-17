from pathlib import Path
from q2sfx.build import Q2SFXBuilder

# Путь к тестовому скрипту
python_app = Path("tests/test_app.py")

builder = Q2SFXBuilder(python_app, console=True)
builder.check_go()
builder.run_pyinstaller()  # соберёт test_app в dist/
builder.pack_payload()  # запакует dist/test_app в zip
builder.prepare_go_files()  # подготовит Go-файлы и payload
builder.build_sfx(Path("test_app_setup.exe"))  # финальный exe
builder.cleanup()
