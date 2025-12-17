from pathlib import Path
from q2sfx.build import Q2SFXBuilder

# Путь к тестовому скрипту

builder = Q2SFXBuilder("tests/test_app.py", console=True)
builder.check_go()
builder.run_pyinstaller()  # соберёт test_app в dist/
builder.pack_payload()  # запакует dist/test_app в zip
builder.prepare_go_files()  # подготовит Go-файлы и payload
builder.build_sfx("test_app_setup.exe")  # финальный exe
builder.cleanup()
