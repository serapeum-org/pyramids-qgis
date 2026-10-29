"""The Pyramids Processing provider: the container QGIS lists under Processing Toolbox.

It registers every algorithm the plugin ships. Adding a new algorithm is one import plus
one entry in :data:`ALGORITHMS` — the provider needs no other change.
"""

from __future__ import annotations

from pathlib import Path

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .algorithms import ALGORITHMS

_ICON = Path(__file__).parent / "resources" / "icon.svg"


class PyramidsProvider(QgsProcessingProvider):
    """Processing provider exposing the pyramids algorithms."""

    def loadAlgorithms(self) -> None:  # noqa: N802  (QGIS-mandated method name)
        """Instantiate and register every algorithm in :data:`ALGORITHMS`."""
        for algorithm_cls in ALGORITHMS:
            self.addAlgorithm(algorithm_cls())

    def id(self) -> str:  # noqa: A003  (QGIS API: the method is named ``id``)
        """Return the stable provider id used in algorithm identifiers (``pyramids:...``)."""
        return "pyramids"

    def name(self) -> str:
        """Return the provider name shown in the Processing Toolbox."""
        return "Pyramids"

    def longName(self) -> str:  # noqa: N802  (QGIS-mandated method name)
        """Return the longer provider description."""
        return "Pyramids GIS toolkit"

    def icon(self) -> QIcon:
        """Return the provider icon, falling back to the QGIS default if missing."""
        if _ICON.is_file():
            return QIcon(str(_ICON))
        return super().icon()

    def supportedOutputVectorLayerExtensions(self) -> list[str]:  # noqa: N802
        """Restrict this provider's vector outputs to GeoJSON.

        The vector-producing algorithms (polygonize, mesh-to-vector) write GeoJSON *content*
        through a forced driver, so the destination extension must be ``.geojson`` too. Without
        this, QGIS's default vector extension (commonly ``.gpkg`` / ``.shp``) would disagree with
        the file content — a file named ``.gpkg`` holding GeoJSON (review M1).
        """
        return ["geojson"]

    def defaultVectorFileExtension(self, hasGeometry: bool = True) -> str:  # noqa: N802, N803
        """Default this provider's vector destinations to ``.geojson``.

        Pairs with :meth:`supportedOutputVectorLayerExtensions` so the chosen extension cannot
        diverge from the forced GeoJSON driver.

        Args:
            hasGeometry: Whether the output layer has geometry (unused; GeoJSON either way).
        """
        return "geojson"
