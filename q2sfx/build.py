# q2sfx/builder.py
import subprocess
import shutil
import zipfile
import tempfile
import sys
from pathlib import Path


class Q2SFXBuilder:
    """
    Builder for creating a self-extracting executable (SFX) from a Python app using PyInstaller and Go.
    """

    def __init__(
        self, python_app: str, console: bool = False, output_dir: str = "dist.sfx"
    ):
        """
        Args:
            python_app (str): Path to the Python entry script.
            console (bool): Run payload with console (True) or GUI (False). Defaults to False.
            output_dir (str): Directory where final SFX will be placed. Defaults to 'dist.sfx'.
        """
        self.python_app = Path(python_app).resolve()
        self.console = console
        self.output_dir = Path(output_dir)
        self.dist_dir = Path("dist")
        self.build_dir = Path("build")
        self.assets_dir = Path(__file__).parent / "assets"
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
        """Run PyInstaller to build the Python app."""
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

        app_base = self.python_app.stem  # root folder inside zip

        with zipfile.ZipFile(
            self.payload_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zf:
            for f in build_folder.rglob("*"):
                relative_path = f.relative_to(build_folder)
                zip_path = Path(app_base) / relative_path
                zf.write(f, zip_path)

        print(f"Payload packed: {self.payload_zip}")

    def prepare_go_files(self):
        """Copy Go files and payload to temp folder for building SFX."""
        temp_go_dir = self.temp_dir / "go_sfx"
        shutil.copytree(self.assets_dir, temp_go_dir, dirs_exist_ok=True)

        payload_dest = temp_go_dir / "payload"
        payload_dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.payload_zip, payload_dest / self.payload_zip.name)

        self.go_sfx_dir = temp_go_dir
        print(f"Go files prepared in {self.go_sfx_dir}")

    def build_sfx(self, output_name: str = None) -> str:
        """
        Build the final self-extracting executable using Go.

        Args:
            output_name (str, optional): Name of the final SFX file. Defaults to Python app stem + .exe on Windows.

        Returns:
            str: Path to the built SFX.
        """
        if not output_name:
            output_name = self.python_app.stem
            if sys.platform.startswith("win"):
                output_name += ".exe"

        final_output = self.output_dir / output_name
        final_output.parent.mkdir(parents=True, exist_ok=True)

        ldflags = "-s -w"
        if self.console:
            ldflags += " -X main.defaultConsole=true"

        cmd = ["go", "build", "-ldflags", ldflags, "-o", str(final_output)]
        print("Building SFX:", " ".join(cmd))
        subprocess.run(cmd, check=True, cwd=self.go_sfx_dir)

        print(f"SFX built: {final_output}")
        return str(final_output)

    def cleanup(self):
        """Remove temporary files created during the build process."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        print(f"Temporary files removed: {self.temp_dir}")
