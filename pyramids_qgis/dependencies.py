"""Runtime checks for the pyramids package inside the QGIS Python environment.

The plugin is a thin adapter: all real work is done by ``pyramids-core``, which must be
importable from the interpreter QGIS runs. Two things can go wrong, and both get a clear,
actionable message instead of a stack trace deep inside an algorithm:

1. ``pyramids`` is not installed in QGIS's Python at all.
2. ``pyramids`` is installed from a *platform wheel that vendors its own GDAL*. Those
   wheels inject a private ``osgeo`` and force ``GDAL_DRIVER_PATH`` at import — safe for a
   standalone process, dangerous inside QGIS, which already has its own GDAL loaded. The
   supported install binds pyramids to QGIS's GDAL (conda-forge, or a plain pip install),
   so we detect the vendored case and warn.
"""

from __future__ import annotations

import importlib.util

_INSTALL_HINT = (
    "The 'pyramids-core' package is not importable from the QGIS Python environment.\n"
    "Install it into the interpreter QGIS runs so it binds to QGIS's own GDAL:\n"
    "  - OSGeo4W / Windows:  open the OSGeo4W shell and run  python -m pip install pyramids-core\n"
    "  - conda-based QGIS:   conda install -c conda-forge pyramids-core\n"
    "  - Linux/macOS:        <qgis-python> -m pip install pyramids-core\n"
    "Do NOT install a platform wheel that vendors its own GDAL inside the QGIS process."
)


def pyramids_installed() -> bool:
    """Return whether the ``pyramids`` package can be located (without importing it)."""
    return importlib.util.find_spec("pyramids") is not None


def ensure_pyramids() -> None:
    """Raise a Processing-friendly error when ``pyramids`` is not importable.

    Raises:
        QgsProcessingException: ``pyramids`` cannot be found in QGIS's Python.
    """
    # Imported lazily so this module is importable (for unit reasoning) without QGIS.
    from qgis.core import QgsProcessingException

    if not pyramids_installed():
        raise QgsProcessingException(_INSTALL_HINT)


def vendored_gdal_warning() -> str | None:
    """Return a warning if the installed pyramids vendors its own GDAL, else ``None``.

    Importing :mod:`pyramids` runs its vendor bootstrap. On a normal (conda-forge / plain
    pip) install this is a no-op and ``osgeo`` resolves to QGIS's GDAL — the supported
    setup. On a platform wheel the bootstrap ships a private ``osgeo`` under the package's
    ``_vendor`` directory, which must not run inside QGIS.

    Returns:
        str | None: A human-readable warning when a vendored GDAL is detected, otherwise
        ``None``. Any import failure is reported as its own warning rather than raised.
    """
    try:
        import pyramids  # noqa: F401  (import for its side-effecting vendor bootstrap)
        from osgeo import gdal
    except Exception as exc:  # noqa: BLE001  (surface any import problem as a soft warning)
        return f"Could not import pyramids / osgeo to verify the GDAL binding: {exc}"

    osgeo_file = getattr(gdal, "__file__", "") or ""
    normalized = osgeo_file.replace("\\", "/").lower()
    if "_vendor" in normalized and "pyramids" in normalized:
        return (
            "The installed pyramids build vendors its own GDAL "
            f"({osgeo_file}). Running it inside QGIS can conflict with QGIS's GDAL. "
            "Reinstall pyramids-core from conda-forge or a plain pip wheel so it uses "
            "QGIS's GDAL."
        )
    return None
