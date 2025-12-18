from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("q2sfx")
except PackageNotFoundError:
    # package is not installed (e.g. editable / source checkout)
    __version__ = "0.0.0"

from .builder import Q2SFXBuilder

__all__ = [
    "Q2SFXBuilder",
    "__version__",
]
