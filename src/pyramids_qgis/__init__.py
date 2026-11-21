"""pyramids-qgis — the pyramids GIS toolkit exposed as a QGIS Processing provider.

QGIS imports this package and looks up ``classFactory`` on it to instantiate the plugin. The
factory is implemented as the snake_case :func:`_class_factory` and exposed under the QGIS-required
``classFactory`` name through PEP 562 module ``__getattr__`` below — so the API QGIS depends on is
unchanged while no camelCase function is declared. Keep this module import-light: QGIS loads it
eagerly for every installed plugin, so the heavy imports (``qgis.core``, ``pyramids``) live behind
the factory, not here.
"""

from __future__ import annotations

import os

# Force host-managed GDAL before `pyramids` is imported anywhere in this process (pyramids-core
# #1588). pyramids-core >= 0.81.0 reads PYRAMIDS_MANAGE_GDAL_ENV: "0" tells it NOT to touch the
# process-global GDAL environment (GDAL_DRIVER_PATH / GDAL_DATA / PROJ_LIB / PATH) and NOT to
# activate its vendored GDAL — so a GDAL-vendoring wheel installed into QGIS's Python leaves QGIS's
# own GDAL intact instead of clobbering it.
#
# Set unconditionally, NOT setdefault: an inherited truthy value (a shell that exported
# PYRAMIDS_MANAGE_GDAL_ENV=1 and then launched QGIS) would make pyramids activate its vendored GDAL
# inside QGIS — exactly the clobber this plugin exists to prevent — so host protection must win here.
#
# Guarantee caveat: this only holds if nothing imported `pyramids` earlier in the process. QGIS loads
# this plugin's __init__ eagerly at startup, but a different plugin that imports pyramids at its own
# module top AND sorts before this one would bootstrap pyramids first; pyramids-core's own best-effort
# host auto-detection is the only backstop in that (unlikely) case.
os.environ["PYRAMIDS_MANAGE_GDAL_ENV"] = "0"


def _class_factory(iface):
    """Return the plugin instance QGIS drives.

    Args:
        iface: The ``QgisInterface`` handle QGIS passes to every plugin.

    Returns:
        PyramidsPlugin: The plugin object exposing ``initGui`` / ``unload``.
    """
    from .plugin import PyramidsPlugin

    return PyramidsPlugin(iface)


def __getattr__(name: str):
    """Expose the QGIS-required ``classFactory`` entry point (PEP 562 module getattr).

    QGIS's plugin loader accesses ``<package>.classFactory``; resolve that to the snake_case
    :func:`_class_factory` on demand, so the entry point exists for QGIS without declaring a
    camelCase function.

    Args:
        name: The attribute QGIS (or anything else) is looking up on this package.

    Returns:
        The ``_class_factory`` callable when ``name`` is ``"classFactory"``.

    Raises:
        AttributeError: For any other attribute name.
    """
    if name == "classFactory":
        return _class_factory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
