from q2sfx.builder import Q2SFXBuilder

# Путь к тестовому скрипту

builder = Q2SFXBuilder("tests/test_app.py", console=True)
builder.run_pyinstaller()  # соберёт test_app в dist/
builder.pack_payload()  # запакует dist/test_app в zip
builder.build_sfx("test_app_setup.exe")  # финальный exe


final_exe = Q2SFXBuilder.build_sfx_from(
    "tests/test_app.py", console=True, output_name="t1.exe"
)
print("Built SFX:", final_exe)


final_exe = Q2SFXBuilder.build_sfx_from(
    dist_path="dist/test_app", console=True, output_name="t2.exe"
)
print("Built SFX:", final_exe)


# final_exe = Q2SFXBuilder.build_sfx_from(
#     payload_zip="dist/test_app.zip", console=True, output_name="t3.exe"
# )
# print("Built SFX:", final_exe)
