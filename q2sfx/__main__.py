# q2sfx/__main__.py

import argparse
import sys
from q2sfx import __version__
from q2sfx import Q2SFXBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Build a self-extracting executable (SFX) "
        "from a Python application using PyInstaller + Go."
    )

    parser.add_argument(
        "app",
        help="Path to the Python entry script (e.g. app.py)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"q2sfx {__version__}",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output SFX file path (default: <app_name>_sfx.exe in dist.sfx)",
        default=None,
    )

    parser.add_argument(
        "--console",
        action="store_true",
        help="Build payload application with console (default: GUI)",
    )

    parser.add_argument(
        "--no-pyinstaller",
        action="store_true",
        help="Assume PyInstaller build already exists (skip PyInstaller step)",
    )

    parser.add_argument(
        "--dist",
        help="Use existing PyInstaller dist directory instead of running PyInstaller",
        default=None,
    )

    parser.add_argument(
        "--payload",
        help="Use existing payload zip instead of creating one",
        default=None,
    )

    parser.add_argument(
        "--build-time",
        help="Build timestamp for .ver file (default: current datetime)",
        default=None,
    )

    parser.add_argument(
        "--no-ver-file",
        action="store_false",
        dest="make_ver_file",
        help="Do not include a .ver file in dist.zip",
    )

    args = parser.parse_args()

    try:
        builder = Q2SFXBuilder(
            args.app,
            console=args.console,
            build_time=args.build_time,
            make_ver_file=args.make_ver_file
        )

        if args.dist:
            builder.set_dist(args.dist)

        if args.payload:
            builder.set_payload(args.payload)

        if not args.no_pyinstaller and not args.dist:
            builder.run_pyinstaller()

        result = builder.build_sfx(args.output)
        print(f"\n✔ SFX successfully built: {result}")

    except Exception as e:
        print(f"\n✖ ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
