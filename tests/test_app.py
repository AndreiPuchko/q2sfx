import sys
import os
import shutil
import subprocess
from pathlib import Path


def read_url(url):
    """
    Read raw bytes from a local file or URL-like path.
    In a real application this can be replaced with:
    - urllib.request.urlopen
    - requests.get
    """
    return open(url, "rb").read()


class App:
    def __init__(self) -> None:
        # Base URL or path where the new build is published
        # Expected files:
        #   test_app_sfx.exe
        #   test_app_sfx.ver
        self.build_url = "../test_app_sfx"

        # Check for updates on startup
        self._check_update()

    def _check_update(self):
        # Only perform update logic when running as a frozen executable (SFX)
        if not getattr(sys, "frozen", False):
            return

        # The .ver file is expected to be next to the executable
        # Example:
        #   test_app.exe
        #   test_app.ver
        ver_file_path = Path(os.path.basename(sys.executable)).with_suffix(".ver")

        if not ver_file_path.is_file():
            # No version file → nothing to compare
            return

        # Read current build timestamp
        current_build_time = ver_file_path.read_text().strip()

        # Read remote build timestamp
        new_build_time = read_url(f"{self.build_url}.ver").decode().strip()

        print("current build:", current_build_time)
        print("new build    :", new_build_time)

        # Simple string comparison works if timestamps are ISO-like:
        # YYYY-MM-DD HH:MM:SS
        if new_build_time > current_build_time:
            input("New build is available. Press Enter to update...")

            # Prepare a clean directory for the new installer
            shutil.rmtree("_new_build", ignore_errors=True)
            os.makedirs("_new_build", exist_ok=True)

            # Download the new SFX executable
            new_build_content = read_url(f"{self.build_url}.exe")
            new_build_path = os.path.join("_new_build", "new_build.exe")

            with open(new_build_path, "wb") as f:
                f.write(new_build_content)

            # Run the new installer in detached mode and exit current app
            subprocess.Popen(
                [new_build_path, "-no-shortcut", "."],
                creationflags=subprocess.DETACHED_PROCESS,
            )
            sys.exit(0)
        else:
            input("No new build found. Press Enter to run the app...")

    def run(self):
        print("Hello from test_app!")
        input("Press Enter to exit...")


if __name__ == "__main__":
    app = App()
    app.run()
