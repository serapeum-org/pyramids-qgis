"""pyramids-qgis — the pyramids GIS toolkit exposed as a QGIS Processing provider.

QGIS imports this package and looks up ``classFactory`` on it to instantiate the plugin. The
factory is implemented as the snake_case :func:`_class_factory` and exposed under the QGIS-required
``classFactory`` name through PEP 562 module ``__getattr__`` below — so the API QGIS depends on is
unchanged while no camelCase function is declared. Keep this module import-light: QGIS loads it
eagerly for every installed plugin, so the heavy imports (``qgis.core``, ``pyramids``) live behind
the factory, not here.
"""

from __future__ import annotations


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
