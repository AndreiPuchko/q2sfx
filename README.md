# q2sfx

**q2sfx** is a Python package and CLI tool to create self-extracting executables (SFX) from Python applications built with PyInstaller.

It embeds your Python application (as a ZIP archive) into a Go-based SFX installer, supports console or GUI modes, and can optionally create a desktop shortcut.

---

## Features

- Build Python apps using PyInstaller (optional, can start from existing build).
- Pack PyInstaller output into a ZIP payload.
- Embed payload into a Go-based self-extracting executable (SFX).
- Supports console or GUI mode.
- Optionally creates a desktop shortcut.
- Fully configurable output directories.
- Works on Windows, Linux, and macOS.

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
git clone <repository_url>
cd q2sfx
poetry install
poetry add --group dev pytest pytest-cov
```

---

## Usage

### Basic usage

from q2sfx.builder import Q2SFXBuilder

builder = Q2SFXBuilder("path/to/your_app.py", console=True)  
builder.build_sfx("dist.sfx/my_app_setup.exe")

This will automatically:

1. Run PyInstaller (if needed).
2. Pack the `dist/your_app` folder into a ZIP payload.
3. Prepare Go files and embed the payload.
4. Build the final SFX executable in `dist.sfx/`.
5. Clean up temporary files.

---

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

### CLI Help

q2_sfx.exe --help

Usage: q2_sfx.exe [options] [path]

Options:  
 -no-shortcut  
 Do not create a desktop shortcut.  
 -shortcut-name string  
 Name of the shortcut (default: application name).

[path] (optional)  
 Installation directory (default: application name).

---

## Building SFX from Python script manually

# Activate your virtual environment

.\.venv\Scripts\activate.ps1

# Run PyInstaller

pyinstaller --console path\to\your_app.py

# Compress the dist folder

Compress-Archive -Path dist\your_app -DestinationPath dist\your_app.zip

# Prepare Go files and build SFX

python -m q2sfx.builder path\to\your_app.py --console

---

## Notes

- The Python application name must match the ZIP archive name.
- By default, SFX will be generated in the `dist.sfx/` folder.
- Desktop shortcut creation is optional.

---

## License

MIT License
