# q2sfx

[**https://github.com/AndreiPuchko/q2sfx**](https://github.com/AndreiPuchko/q2sfx)

**q2sfx** is a Python package and CLI tool to create self-extracting executables (SFX) from Python applications built with PyInstaller.


It embeds your Python application (as a ZIP archive) into a Go-based SFX installer, supports console or GUI modes, and can optionally create a desktop shortcut.

---

## ✨ Key Features

- Build Python apps using PyInstaller (optional, can start from existing build).
- Pack PyInstaller output into a ZIP payload (optional, can start from existing ZIP).
- Embed payload into a Go-based self-extracting executable (SFX).

## The generated SFX executable provides:

- **Installer**: on the first run extracts all payload data (PyApp) into the given folder(optional), creates the shortcut (optional) and runs PyApp.
- **Updater**: When updating, the tool only overwrites core components (`.exe`, `.ver`, `_internal/`, and `assets/`) and runs PyApp. Custom user folders, logs, or local databases remain untouched.
  Before overwriting, existing core files and directories are automatically
  backed up as `.bak`. A platform-specific rollback script
  (`_rollback.bat` on Windows or `_rollback.sh` on Linux/macOS) is generated,
  allowing the previous version to be fully restored if needed.
- **CLI Flexibility**: SFX Supports flags to force console mode, change the installation path or shortcut name.
- Progress bar with animated spinner.
- Cross-platform: Windows, Linux, macOS.

- **Progress indication during extraction**, including an animated spinner.
- **Safe overwrite behavior** — only predefined folders and files are modified
  (`_internal`, `assets`, and the executable itself), preventing accidental data loss.

---

## Requirements

- Python 3.8–3.11
- Go (for building the SFX)
- PyInstaller (if you want the builder to run it automatically)

---

## Installation

### For End Users

Install `q2sfx` as a Python package via Poetry:

```bash
poetry add q2sfx
```

or

```bash
pip install q2sfx
```

### For Developers

```bash
git clone https://github.com/AndreiPuchko/q2sfx
cd q2sfx
poetry install
poetry add --group dev pytest pytest-cov
```

---

## Usage

### CLI usage

```
q2sfx --help
usage: q2sfx [-h] [--version] [-o OUTPUT] [--console] [--no-pyinstaller] [--dist DIST] [--payload PAYLOAD] [--build-time BUILD_TIME] [--no-ver-file] app

Build a self-extracting executable (SFX) from a Python application using PyInstaller + Go.

positional arguments:
  app                   Path to the Python entry script (e.g. app.py)

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -o OUTPUT, --output OUTPUT
                        Output SFX file path (default: <app_name>_sfx.exe in dist.sfx)
  --console             Build payload application with console (default: GUI)
  --no-pyinstaller      Assume PyInstaller build already exists (skip PyInstaller step)
  --dist DIST           Use existing PyInstaller dist directory instead of running PyInstaller
  --payload PAYLOAD     Use existing payload zip instead of creating one
  --build-time BUILD_TIME
                        Build timestamp for .ver file (default: current datetime)
  --no-ver-file         Do not include a .ver file in dist.zip
```

### Basic usage

**Build a console application from Python code**  
This runs PyInstaller with default options and wraps the result into an SFX.

```python
from q2sfx import Q2SFXBuilder

final_exe = Q2SFXBuilder.build_sfx_from("tests/test_app.py", console=True)
print("Built SFX:", final_exe)
```

**Build an SFX from an existing PyInstaller dist/ directory**
Useful when PyInstaller requires custom options or hooks.

```python
final_exe = Q2SFXBuilder.build_sfx_from(dist_path="dist/test_app", output_name="t2.exe")
print("Built SFX:", final_exe)
```

**Build an SFX from a ZIP payload**
Useful when your distribution contains extra assets or was prepared externally.

```python
final_exe = Q2SFXBuilder.build_sfx_from(payload_zip="dist.zip/test_app.zip", output_name="t3.exe")
print("Built SFX:", final_exe)
```

### Advanced usage

You can start the builder from any stage:

builder = Q2SFXBuilder("your_app.py", console=True)

# Use an existing PyInstaller dist folder

builder.set_dist("dist/your_app")

# Or use an existing ZIP payload

builder.set_payload("dist/your_app.zip")

# Build SFX

builder.build_sfx("dist.sfx/my_app_setup.exe")

---

## ZIP file notes

- The Python application name must match the ZIP archive name.
- By default, SFX will be generated in the `dist.sfx/` folder.

---

# Simple Auto-update example

![Source Code](https://img.shields.io/badge/source-github-blue)(https://github.com/AndreiPuchko/q2sfx/blob/main/tests/test_app.py)

Each SFX build produced by **q2sfx** can include a `.ver` file containing
the build timestamp (for example: `2025-12-31 18:42:10`).

The application can compare its local `.ver` file with a remote one
and automatically download and run a newer SFX build.

#### Expected files on the update server

`test_app_sfx.exe`
`test_app_sfx.ver`

#### How it works

1. On startup, the application checks whether it is running as a frozen executable.
2. It reads its local `<app>.ver` file.
3. It downloads and compares the remote `.ver` file.
4. If a newer build is available:
   - the new SFX is downloaded
   - launched in detached mode
   - the current application exits
5. The new SFX handles safe replacement and rollback internally
   (`.bak` files + `_rollback.bat` / `_rollback.sh`) and starts updated app

#### Example update logic

```python
if new_build_time > current_build_time:
    # download new SFX
    # run installer
    # exit current app
```

---
# Simple GUI demo workflow (for Windows)
```bash
# create virtual enviroment (python 3.9 used)
py -3.9 -m venv .venv
# activate virtual enviroment
.\.venv\Scripts\activate
# install deps for demo project
pip install q2db q2gui
pip install git+https://github.com/AndreiPuchko/q2sfx.git
# clone demo project
git clone https://github.com/AndreiPuchko/q2-short.git
# build SFX
q2sfx .\q2-short\app.py
# run the result
cd dist.sfx
./app_sfx.exe
```

---

## License

MIT License
