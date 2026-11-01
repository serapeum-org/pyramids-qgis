"""The QGIS plugin shell: register and unregister the Pyramids Processing provider.

This plugin is Processing-only (``hasProcessingProvider=yes`` in ``metadata.txt``), so enabling it
does nothing but add the provider to the Processing registry, and ``unload`` removes it. There is no
toolbar or menu action to manage. QGIS's ``initGui`` lifecycle hook is implemented as the snake_case
:meth:`PyramidsPlugin._init_gui` and exposed under the ``initGui`` name via ``__getattr__``, so the
method QGIS calls exists without a camelCase declaration.
"""

from __future__ import annotations

from qgis.core import QgsApplication

from .provider import PyramidsProvider


class PyramidsPlugin:
    """Thin lifecycle wrapper that owns the Processing provider."""

    def __init__(self, iface):
        """Store the QGIS interface handle and defer provider creation to ``initGui``.

        Args:
            iface: The ``QgisInterface`` passed by QGIS.
        """
        self.iface = iface
        self.provider: PyramidsProvider | None = None

    def init_processing(self) -> None:
        """Create the provider and add it to the Processing registry."""
        self.provider = PyramidsProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def _init_gui(self) -> None:
        """Enable the plugin: register the Processing provider.

        QGIS reaches this through the ``initGui`` name exposed by :meth:`__getattr__`.
        """
        self.init_processing()

    def unload(self) -> None:
        """Remove the provider when the plugin is disabled or QGIS shuts down."""
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

    def __getattr__(self, name: str):
        """Expose the QGIS-required ``initGui`` lifecycle method dynamically.

        QGIS enables the plugin by calling ``initGui``; resolve that to the snake_case
        :meth:`_init_gui` on demand so the method QGIS needs exists without declaring a camelCase
        method. ``__getattr__`` only runs for attributes normal lookup does not find, so every real
        attribute (``iface``, ``provider``, ``_init_gui``, ``unload``, …) is unaffected.

        Args:
            name: The attribute being looked up on the instance.

        Returns:
            The bound ``_init_gui`` method when ``name`` is ``"initGui"``.

        Raises:
            AttributeError: For any other attribute name.
        """
        if name == "initGui":
            return self._init_gui
        raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")
