"""The QGIS plugin shell: register and unregister the Pyramids Processing provider.

This plugin is Processing-only (``hasProcessingProvider=yes`` in ``metadata.txt``), so
``initGui`` does nothing but add the provider to the Processing registry, and ``unload``
removes it. There is no toolbar or menu action to manage.
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

    def initGui(self) -> None:  # noqa: N802  (QGIS-mandated method name)
        """QGIS entry point called when the plugin is enabled."""
        self.init_processing()

    def unload(self) -> None:
        """Remove the provider when the plugin is disabled or QGIS shuts down."""
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
