"""pyramids-qgis — the pyramids GIS toolkit exposed as a QGIS Processing provider.

QGIS imports this package and calls :func:`classFactory` to instantiate the plugin.
Keep this module import-light: QGIS loads it eagerly for every installed plugin, so
the heavy imports (``qgis.core``, ``pyramids``) live behind the factory, not here.
"""

from __future__ import annotations


def classFactory(iface):  # noqa: N802 # NOSONAR(python:S1542) QGIS imports/calls this exact name
    """Return the plugin instance QGIS drives.

    Args:
        iface: The ``QgisInterface`` handle QGIS passes to every plugin.

    Returns:
        PyramidsPlugin: The plugin object exposing ``initGui`` / ``unload``.
    """
    from .plugin import PyramidsPlugin

    return PyramidsPlugin(iface)
