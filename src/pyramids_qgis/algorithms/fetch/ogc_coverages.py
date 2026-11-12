"""Fetch a window from an OGC API - Coverages service — wraps ``pyramids fetch ogc-coverages``."""

from __future__ import annotations

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingException,
    QgsProcessingParameterCrs,
    QgsProcessingParameterExtent,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, crs_to_pyramids


class FetchOgcCoverages(PyramidsAlgorithm):
    """Request a coverage window from an OGC API - Coverages service and write it as a raster."""

    GROUP_LABEL = "Fetch"
    GROUP_ID = "fetch"

    ENDPOINT = "ENDPOINT"
    COVERAGE = "COVERAGE"
    EXTENT = "EXTENT"
    RESOLUTION = "RESOLUTION"
    COVERAGE_CRS = "COVERAGE_CRS"
    OUTPUT_CRS = "OUTPUT_CRS"
    RESAMPLE = "RESAMPLE"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "fetch_ogc_coverages"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Fetch OGC API Coverages window"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Request a single coverage window from an OGC API - Coverages service and save it "
            "as a raster. Give the API landing-page/base URL, the coverage identifier, and the "
            "request extent (sent in lon/lat). Optionally set an approximate pixel size, supply "
            "a coverage CRS when the service omits one, reproject the result to another CRS, "
            "and choose a resampling method."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(
            QgsProcessingParameterString(self.ENDPOINT, "OGC API landing-page / base URL")
        )
        self.addParameter(QgsProcessingParameterString(self.COVERAGE, "Coverage identifier"))
        self.addParameter(QgsProcessingParameterExtent(self.EXTENT, "Request extent"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RESOLUTION,
                "Approximate pixel size in the coverage's native CRS units (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                self.COVERAGE_CRS,
                "Coverage CRS when the service omits one (optional)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                self.OUTPUT_CRS, "Reproject the result to this CRS (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.RESAMPLE, "Resampling method (optional; default: nearest)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Fetched raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids fetch ogc-coverages`` command."""
        endpoint = self.parameterAsString(parameters, self.ENDPOINT, context).strip()
        if not endpoint:
            raise QgsProcessingException("An OGC API landing-page / base URL is required.")
        coverage = self.parameterAsString(parameters, self.COVERAGE, context).strip()
        if not coverage:
            raise QgsProcessingException("A coverage identifier is required.")
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["fetch", "ogc-coverages", endpoint, out, "--coverage", coverage]

        # The service has no bbox-CRS flag; the request window is sent in lon/lat (EPSG:4326).
        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        extent = self.parameterAsExtent(parameters, self.EXTENT, context, wgs84)
        if extent.isNull():
            raise QgsProcessingException("A request extent is required.")
        argv += [
            "--bbox",
            str(extent.xMinimum()),
            str(extent.yMinimum()),
            str(extent.xMaximum()),
            str(extent.yMaximum()),
        ]

        if self.RESOLUTION in parameters and parameters[self.RESOLUTION] is not None:
            resolution = self.parameterAsDouble(parameters, self.RESOLUTION, context)
            argv += ["--resolution", str(resolution)]
        coverage_crs = crs_to_pyramids(self.parameterAsCrs(parameters, self.COVERAGE_CRS, context))
        if coverage_crs:
            argv += ["--coverage-crs", coverage_crs]
        output_crs = crs_to_pyramids(self.parameterAsCrs(parameters, self.OUTPUT_CRS, context))
        if output_crs:
            argv += ["--output-crs", output_crs]
        resample = self.parameterAsString(parameters, self.RESAMPLE, context).strip()
        if resample:
            argv += ["--resample", resample]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
