"""Fetch features from a WFS service — wraps ``pyramids fetch wfs``."""

from __future__ import annotations

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingException,
    QgsProcessingParameterExtent,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
)

from ..base import PyramidsAlgorithm


class FetchWfs(PyramidsAlgorithm):
    """Request a feature type from a WFS endpoint and write it as a vector layer."""

    GROUP_LABEL = "Fetch"
    GROUP_ID = "fetch"

    URL = "URL"
    TYPENAME = "TYPENAME"
    EXTENT = "EXTENT"
    DRIVER = "DRIVER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "fetch_wfs"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Fetch WFS features"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Request a feature type from a WFS endpoint and save it as a vector layer. Give the "
            "service URL and the feature type name. Optionally restrict the request to an extent "
            "(sent in lon/lat). The OGR driver defaults to GeoJSON unless an explicit driver "
            "name is given."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterString(self.URL, "WFS endpoint URL"))
        self.addParameter(QgsProcessingParameterString(self.TYPENAME, "Feature type name"))
        self.addParameter(
            QgsProcessingParameterExtent(self.EXTENT, "Request extent (optional)", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DRIVER, "Driver (optional; default: geojson)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Fetched vector"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids fetch wfs`` command."""
        url = self.parameterAsString(parameters, self.URL, context).strip()
        if not url:
            raise QgsProcessingException("A WFS endpoint URL is required.")
        typename = self.parameterAsString(parameters, self.TYPENAME, context).strip()
        if not typename:
            raise QgsProcessingException("A feature type name is required.")
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["fetch", "wfs", url, out, "--typename", typename]

        if self.EXTENT in parameters and parameters[self.EXTENT] is not None:
            # The service has no bbox-CRS flag; the request window is sent in lon/lat (EPSG:4326).
            wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
            extent = self.parameterAsExtent(parameters, self.EXTENT, context, wgs84)
            if not extent.isNull():
                argv += [
                    "--bbox",
                    str(extent.xMinimum()),
                    str(extent.yMinimum()),
                    str(extent.xMaximum()),
                    str(extent.yMaximum()),
                ]

        driver = self.parameterAsString(parameters, self.DRIVER, context).strip()
        if driver:
            argv += ["--driver", driver]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
