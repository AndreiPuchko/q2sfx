from importlib.metadata import version, PackageNotFoundError
from version import __version__

from .builder import Q2SFXBuilder

__all__ = [
    "Q2SFXBuilder",
    "__version__",
]
