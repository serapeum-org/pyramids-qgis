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
from pathlib import Path

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


_EO_HINT = (
    "pyramids-eo is not installed, so the Earth-observation algorithms are unavailable.\n"
    "Install it into the QGIS Python environment:\n"
    "  <qgis-python> -m pip install pyramids-eo"
)


def pyramids_eo_installed() -> bool:
    """Return whether the ``pyramids_eo`` package can be located."""
    return importlib.util.find_spec("pyramids_eo") is not None


def ensure_pyramids_eo() -> None:
    """Raise a Processing-friendly error when ``pyramids_eo`` is not importable.

    Unlike pyramids-mesh (optional, soft warning), pyramids-eo is a hard requirement for the
    Earth-observation algorithms — without it there is nothing to run.

    Raises:
        QgsProcessingException: ``pyramids_eo`` cannot be found in QGIS's Python.
    """
    from qgis.core import QgsProcessingException

    if not pyramids_eo_installed():
        raise QgsProcessingException(_EO_HINT)


_MESH_DRIVERS_HINT = (
    "pyramids-mesh is not installed, so only UGRID NetCDF meshes can be read or written.\n"
    "Install it into the QGIS Python environment to enable the other mesh formats "
    "(2DM, Selafin, DFSU, XMDF, PLY, ...):\n"
    "  <qgis-python> -m pip install pyramids-mesh"
)


def pyramids_mesh_installed() -> bool:
    """Return whether the ``pyramids_mesh`` driver package can be located."""
    return importlib.util.find_spec("pyramids_mesh") is not None


def mesh_drivers_warning() -> str | None:
    """Return a hint when pyramids-mesh is absent, else ``None``.

    pyramids-mesh is optional: the built-in UGRID NetCDF read/write works without it, but every
    other mesh format (2DM, Selafin, DFSU, ...) is provided by a pyramids-mesh driver. This is a
    soft warning, not an error — a NetCDF-only workflow is fine without it.

    Returns:
        str | None: The install hint when pyramids-mesh is missing, otherwise ``None``.
    """
    if not pyramids_mesh_installed():
        return _MESH_DRIVERS_HINT
    return None


def vendored_gdal_warning() -> str | None:
    """Return a warning if the installed pyramids vendors its own GDAL, else ``None``.

    A platform wheel ships a private ``osgeo`` under the package's ``_vendor`` directory and
    activates it on import; that build must not run inside QGIS, which already has its own GDAL
    loaded. Detection is by **filesystem**: the installed ``pyramids`` package is located with
    :func:`importlib.util.find_spec` (which does not import it) and checked for a
    ``_vendor/osgeo`` directory. This is deliberately independent of what ``osgeo`` is already
    imported — inspecting ``osgeo.__file__`` would return QGIS's cached module once QGIS has
    imported its own GDAL, hiding a genuinely vendored pyramids build (review L2).

    Returns:
        str | None: A human-readable warning when a vendored build is detected on disk,
        otherwise ``None`` (including when pyramids is not installed — that case is reported by
        :func:`ensure_pyramids`, not here).
    """
    try:
        spec = importlib.util.find_spec("pyramids")
    except (ImportError, ValueError):  # a broken/partial install can raise from find_spec
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    for location in spec.submodule_search_locations:
        # `_vendor/osgeo` is not a guess: it is the exact location pyramids' own runtime bootstrap
        # ships and activates the vendored SWIG bindings from — see pyramids/base/_bootstrap.py
        # (`pyramids/_vendor/osgeo/`), which `pyramids/__init__.py` calls via activate_vendored_osgeo.
        # If pyramids ever changes that layout, update this path to match (review R2-L2).
        vendored = Path(location) / "_vendor" / "osgeo"
        if vendored.is_dir():
            return (
                f"The installed pyramids build vendors its own GDAL (at {vendored}). "
                "Running it inside QGIS can conflict with QGIS's GDAL. Reinstall pyramids-core "
                "from conda-forge or a plain pip wheel so it uses QGIS's GDAL."
            )
    return None
