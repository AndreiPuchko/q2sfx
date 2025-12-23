from q2sfx import Q2SFXBuilder

# Путь к тестовому скрипту

builder = Q2SFXBuilder("tests/test_app.py")
builder.run_pyinstaller()  # builds test_app в dist/
builder.pack_payload()  # packs dist/test_app в zip
builder.build_sfx("test_app_setup.exe")  # final sfx exe


final_exe = Q2SFXBuilder.build_sfx_from("tests/test_app.py", output_name="t1.exe")
print("Built SFX:", final_exe)


final_exe = Q2SFXBuilder.build_sfx_from(dist_path="dist/test_app", output_name="t2.exe")
print("Built SFX:", final_exe)


final_exe = Q2SFXBuilder.build_sfx_from(
    payload_zip="dist.zip/test_app.zip", output_name="t3.exe"
)
print("Built SFX:", final_exe)
