# q2sfx/builder.py
import subprocess
import shutil
import zipfile
import tempfile
import sys
from pathlib import Path


class Q2SFXBuilder:
    """
    Builder for creating a self-extracting executable (SFX) from a Python app.
    Supports starting from any stage: source script, PyInstaller dist, or payload zip.
    """

    def __init__(
        self,
        python_app: str = "",
        console: bool = True,
        output_dir: str = "dist.sfx",
    ):
        self.python_app = Path(python_app).resolve() if python_app else None
        self.console = console

        # Directories (can be overridden)
        self.output_dir = Path(output_dir)
        self.dist_dir = Path("dist")
        self.build_dir = Path("build")
        self.assets_dir = Path(__file__).parent / "assets"
        self.dist_is_ready = False

        self.temp_dir = Path(tempfile.mkdtemp())
        self.payload_zip = None
        self.go_sfx_dir = None
        self.check_go()

    # --------------------- Stage setters ---------------------

    def set_dist(self, dist_path: str):
        """Use an existing PyInstaller dist folder instead of building it."""
        self.dist_dir = Path(dist_path).resolve()
        if not self.python_app:
            # Try to infer python_app stem from dist folder name
            self.python_app = Path(dist_path).name
        self.dist_is_ready = True
        return self

    def set_payload(self, payload_zip: str):
        """Use an existing payload zip instead of packing it."""
        self.payload_zip = Path(payload_zip).resolve()
        if not self.payload_zip.exists():
            raise RuntimeError("payload_zip not found")
        return self

    def set_output_dir(self, output_dir: str):
        """Change the directory where final SFX will be placed."""
        self.output_dir = Path(output_dir).resolve()
        return self

    def set_assets_dir(self, assets_dir: str):
        """Change the directory containing Go assets."""
        self.assets_dir = Path(assets_dir).resolve()
        return self

    # --------------------- Core stages ---------------------

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
        return self

    def run_pyinstaller(self):
        """Run PyInstaller to build the Python app (optional)."""
        if not self.python_app or not self.python_app.exists():
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
            "--specpath",
            str(self.build_dir),
            str(self.python_app),
        ]
        if not self.console:
            cmd.append("--windowed")

        print("Running PyInstaller:", " ".join(cmd))
        subprocess.run(cmd, check=True)
        self.dist_is_ready = True
        return self

    def pack_payload(self):
        """Zip the PyInstaller dist folder into a payload zip."""
        if self.payload_zip and self.payload_zip.exists():
            # payload already set
            return self

        if self.dist_is_ready:
            dist_folder = self.dist_dir
        else:
            if self.python_app is None:
                raise RuntimeError("python_app not set")
            dist_folder = (
                self.dist_dir / self.python_app.stem
                if isinstance(self.python_app, Path)
                else self.dist_dir / self.python_app
            )
        
        if not dist_folder.exists() or self.dist_is_ready is False:
            print(
                f"Dist folder {dist_folder} not found. Running PyInstaller automatically..."
            )
            self.run_pyinstaller()
            dist_folder = self.dist_dir / self.python_app.stem

        if not self.dist_dir or not self.python_app:
            raise RuntimeError("dist_dir or python_app not set")

        self.payload_zip = self.temp_dir / f"{dist_folder.name}.zip"
        app_base = dist_folder.name

        with zipfile.ZipFile(
            self.payload_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zf:
            for f in dist_folder.rglob("*"):
                relative_path = f.relative_to(dist_folder)
                zip_path = Path(app_base) / relative_path
                zf.write(f, zip_path)

        print(f"Payload packed: {self.payload_zip}")
        return self

    def prepare_go_files(self):
        """Copy Go files and payload to temp folder for building SFX."""
        if not self.payload_zip or not self.payload_zip.exists():
            print("Payload not found. Packing automatically...")
            self.pack_payload()

        temp_go_dir = self.temp_dir / "go_sfx"
        shutil.copytree(self.assets_dir, temp_go_dir, dirs_exist_ok=True)

        payload_dest = temp_go_dir / "payload"
        payload_dest.mkdir(parents=True, exist_ok=True)
        if not self.payload_zip:
            raise RuntimeError("payload_zip not set")
        shutil.copy(self.payload_zip, payload_dest / self.payload_zip.name)

        self.go_sfx_dir = temp_go_dir
        print(f"Go files prepared in {self.go_sfx_dir}")
        return self

    def build_sfx(self, output_name: str = None) -> str:
        """
        Build the final SFX executable using Go.

        Args:
            output_name (str, optional): Name of the final SFX file.

        Returns:
            str: Path to the built SFX.
        """
        if not self.go_sfx_dir:
            self.prepare_go_files()

        if not output_name:
            output_name = (
                self.python_app.stem
                if isinstance(self.python_app, Path)
                else str(self.python_app)
            )
            if sys.platform.startswith("win"):
                output_name += ".exe"

        final_output = (Path.cwd() / self.output_dir / output_name).resolve()
        final_output.parent.mkdir(parents=True, exist_ok=True)

        ldflags = "-s -w"
        if self.console:
            ldflags += " -X main.defaultConsole=true"

        print(
            "Building SFX:",
            " ".join(["go", "build", "-ldflags", ldflags, "-o", str(final_output)]),
        )
        subprocess.run(
            ["go", "build", "-ldflags", ldflags, "-o", str(final_output)],
            check=True,
            cwd=self.go_sfx_dir,
        )

        print(f"SFX built: {final_output}")
        self.cleanup()
        return str(final_output)

    def cleanup(self):
        """Remove temporary files created during the build process."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        print(f"Temporary files removed: {self.temp_dir}")
        return self

    # --------------------- Factory ---------------------

    @staticmethod
    def build_sfx_from(
        python_app: str = "",
        dist_path: str = "",
        payload_zip: str = "",
        output_dir: str = "dist.sfx",
        console: bool = True,
        output_name: str = "",
    ) -> str:
        """
        Convenience factory: build SFX in one line from any stage.
        Will automatically run PyInstaller / pack / prepare as needed.
        """
        builder = Q2SFXBuilder(
            python_app=python_app, console=console, output_dir=output_dir
        )
        if dist_path:
            builder.set_dist(dist_path)
        if payload_zip:
            builder.set_payload(payload_zip)
        return builder.build_sfx(output_name)
