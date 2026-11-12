"""Fetch a window from a WMS service — wraps ``pyramids fetch wms``."""

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


class FetchWms(PyramidsAlgorithm):
    """Request a map window from a WMS endpoint and write it as a raster."""

    GROUP_LABEL = "Fetch"
    GROUP_ID = "fetch"

    URL = "URL"
    LAYERS = "LAYERS"
    EXTENT = "EXTENT"
    CRS = "CRS"
    WIDTH = "WIDTH"
    HEIGHT = "HEIGHT"
    RESOLUTION = "RESOLUTION"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "fetch_wms"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Fetch WMS window"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Request a single window from a WMS endpoint and save it as a raster. Give the "
            "service URL, the WMS layer name, and the request extent. The extent is sent in "
            "lon/lat unless a request CRS is chosen. Set either the output pixel size (width "
            "and height) or an output cell size in CRS units."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterString(self.URL, "WMS endpoint URL"))
        self.addParameter(QgsProcessingParameterString(self.LAYERS, "WMS layer name"))
        self.addParameter(QgsProcessingParameterExtent(self.EXTENT, "Request extent"))
        self.addParameter(
            QgsProcessingParameterCrs(
                self.CRS, "Request CRS (optional; default: the service default)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.WIDTH,
                "Output width in pixels (with height)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.HEIGHT,
                "Output height in pixels (with width)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RESOLUTION,
                "Output cell size in CRS units (instead of width/height)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Fetched raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids fetch wms`` command."""
        url = self.parameterAsString(parameters, self.URL, context).strip()
        if not url:
            raise QgsProcessingException("A WMS endpoint URL is required.")
        layers = self.parameterAsString(parameters, self.LAYERS, context).strip()
        if not layers:
            raise QgsProcessingException("A WMS layer name is required.")
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["fetch", "wms", url, out, "--layers", layers]

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

        has_width = self.WIDTH in parameters and parameters[self.WIDTH] is not None
        has_height = self.HEIGHT in parameters and parameters[self.HEIGHT] is not None
        has_resolution = self.RESOLUTION in parameters and parameters[self.RESOLUTION] is not None
        if has_width and has_height:
            width = self.parameterAsInt(parameters, self.WIDTH, context)
            height = self.parameterAsInt(parameters, self.HEIGHT, context)
            argv += ["--size", str(width), str(height)]
        elif has_resolution:
            resolution = self.parameterAsDouble(parameters, self.RESOLUTION, context)
            argv += ["--resolution", str(resolution)]
        else:
            raise QgsProcessingException(
                "Provide either the output size (both width and height) or an output cell size."
            )
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
