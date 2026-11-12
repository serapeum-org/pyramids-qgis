"""Fetch a window from a WCS service — wraps ``pyramids fetch wcs``."""

from __future__ import annotations

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingException,
    QgsProcessingParameterCrs,
    QgsProcessingParameterExtent,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, crs_to_pyramids


class FetchWcs(PyramidsAlgorithm):
    """Request a coverage window from a WCS endpoint and write it as a raster."""

    GROUP_LABEL = "Fetch"
    GROUP_ID = "fetch"

    URL = "URL"
    COVERAGE = "COVERAGE"
    EXTENT = "EXTENT"
    CRS = "CRS"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "fetch_wcs"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Fetch WCS window"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Request a single coverage window from a WCS endpoint and save it as a raster. "
            "Give the service URL, the coverage identifier, and the request extent. The extent "
            "is sent in lon/lat unless a bbox CRS is chosen."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterString(self.URL, "WCS endpoint URL"))
        self.addParameter(QgsProcessingParameterString(self.COVERAGE, "Coverage identifier"))
        self.addParameter(QgsProcessingParameterExtent(self.EXTENT, "Request extent"))
        self.addParameter(
            QgsProcessingParameterCrs(
                self.CRS, "Bbox CRS (optional; default: the service default)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Fetched raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids fetch wcs`` command."""
        url = self.parameterAsString(parameters, self.URL, context).strip()
        if not url:
            raise QgsProcessingException("A WCS endpoint URL is required.")
        coverage = self.parameterAsString(parameters, self.COVERAGE, context).strip()
        if not coverage:
            raise QgsProcessingException("A coverage identifier is required.")
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["fetch", "wcs", url, out, "--coverage", coverage]

        crs = self.parameterAsCrs(parameters, self.CRS, context)
        bbox_crs = crs if crs.isValid() else QgsCoordinateReferenceSystem("EPSG:4326")
        extent = self.parameterAsExtent(parameters, self.EXTENT, context, bbox_crs)
        if extent.isNull():
            raise QgsProcessingException("A request extent is required.")
        argv += [
            "--bbox",
            str(extent.xMinimum()),
            str(extent.yMinimum()),
            str(extent.xMaximum()),
            str(extent.yMaximum()),
        ]
        crs_str = crs_to_pyramids(crs)
        if crs_str:
            argv += ["--crs", crs_str]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
