# q2sfx/builder.py
import subprocess
import shutil
from pathlib import Path
import zipfile
import tempfile
import sys


class Q2SFXBuilder:
    def __init__(self, python_app: Path, console: bool = False):
        self.python_app = python_app.resolve()
        self.console = console
        self.dist_dir = Path("dist")
        self.build_dir = Path("build")
        self.assets_dir = Path(__file__).parent / "assets"  # Go файлы здесь
        self.temp_dir = Path(tempfile.mkdtemp())
        self.payload_zip = self.temp_dir / f"{self.python_app.stem}.zip"
        self.go_sfx_dir = None

    def check_go(self):
        """Check if Go is installed."""
        try:
            subprocess.run(
                ["go", "version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            raise RuntimeError("Go is not installed or not in PATH")

    def run_pyinstaller(self):
        """Run PyInstaller to build the Python app (optional)."""
        if not self.python_app.exists():
            raise FileNotFoundError(f"{self.python_app} does not exist")
        self.dist_dir.mkdir(parents=True, exist_ok=True)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--distpath",
            str(self.dist_dir),
            "--workpath",
            str(self.build_dir),
            str(self.python_app),
        ]
        if not self.console:
            cmd.append("--windowed")
        print("Running PyInstaller:", " ".join(cmd))
        subprocess.run(cmd, check=True)

    def pack_payload(self):
        """Zip the PyInstaller build folder for embedding into SFX."""
        build_folder = self.dist_dir / self.python_app.stem
        if not build_folder.exists():
            raise FileNotFoundError(
                f"PyInstaller output folder {build_folder} does not exist"
            )

        app_base = self.python_app.stem  # имя корневой папки внутри zip

        with zipfile.ZipFile(
            self.payload_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zf:
            for f in build_folder.rglob("*"):
                relative_path = f.relative_to(build_folder)
                # добавляем app_base как корень внутри архива
                zip_path = Path(app_base) / relative_path
                zf.write(f, zip_path)

        print(f"Payload packed: {self.payload_zip}")

    def prepare_go_files(self):
        """Copy Go files and payload to temp folder for building SFX."""
        temp_go_dir = self.temp_dir / "go_sfx"
        # Копируем все файлы из assets
        shutil.copytree(self.assets_dir, temp_go_dir, dirs_exist_ok=True)
        # Копируем архив payload внутрь
        payload_dest = temp_go_dir / "payload"
        payload_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.payload_zip, payload_dest / self.payload_zip.name)
        self.go_sfx_dir = temp_go_dir
        print(f"Go files prepared in {self.go_sfx_dir}")

    def build_sfx(self, output: Path):
        """Run Go build to create final SFX executable."""
        output = Path(output).resolve()
        ldflags = "-s -w"
        if self.console:
            ldflags += " -X main.defaultConsole=true"
        cmd = ["go", "build", "-ldflags", ldflags, "-o", str(output)]
        print("Building SFX:", " ".join(cmd))
        subprocess.run(cmd, check=True, cwd=self.go_sfx_dir)
        print(f"SFX built: {output}")

    def cleanup(self):
        """Remove temporary files."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        print(f"Temporary files removed: {self.temp_dir}")
