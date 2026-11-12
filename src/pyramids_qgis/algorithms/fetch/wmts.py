"""Fetch a window from a WMTS service — wraps ``pyramids fetch wmts``."""

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


class FetchWmts(PyramidsAlgorithm):
    """Request a window from a WMTS endpoint and write it as a raster."""

    GROUP_LABEL = "Fetch"
    GROUP_ID = "fetch"

    ENDPOINT = "ENDPOINT"
    LAYER = "LAYER"
    EXTENT = "EXTENT"
    CRS = "CRS"
    TILE_MATRIX_SET = "TILE_MATRIX_SET"
    RESOLUTION = "RESOLUTION"
    LAYER_CRS = "LAYER_CRS"
    OUTPUT_CRS = "OUTPUT_CRS"
    RESAMPLE = "RESAMPLE"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "fetch_wmts"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Fetch WMTS window"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Request a single window from a WMTS service and save it as a raster. Give the "
            "GetCapabilities URL, the layer identifier, and the request extent (sent in "
            "EPSG:4326 unless a bbox CRS is chosen). Optionally pin a tile-matrix-set, set an "
            "output cell size, supply a layer CRS when the service omits one, reproject the "
            "result to another CRS, and choose a resampling method."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterString(self.ENDPOINT, "WMTS GetCapabilities URL"))
        self.addParameter(QgsProcessingParameterString(self.LAYER, "WMTS layer identifier"))
        self.addParameter(QgsProcessingParameterExtent(self.EXTENT, "Request extent"))
        self.addParameter(
            QgsProcessingParameterCrs(
                self.CRS, "Bbox CRS (optional; default: EPSG:4326)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.TILE_MATRIX_SET, "Tile-matrix-set id to pin (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RESOLUTION,
                "Output pixel size in the layer's native CRS units (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                self.LAYER_CRS, "Layer CRS when the service omits one (optional)", optional=True
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
        """Build and run the ``pyramids fetch wmts`` command."""
        endpoint = self.parameterAsString(parameters, self.ENDPOINT, context).strip()
        if not endpoint:
            raise QgsProcessingException("A WMTS GetCapabilities URL is required.")
        layer = self.parameterAsString(parameters, self.LAYER, context).strip()
        if not layer:
            raise QgsProcessingException("A WMTS layer identifier is required.")
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["fetch", "wmts", endpoint, out, "--layer", layer]

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

        tile_matrix_set = self.parameterAsString(parameters, self.TILE_MATRIX_SET, context).strip()
        if tile_matrix_set:
            argv += ["--tile-matrix-set", tile_matrix_set]
        if self.RESOLUTION in parameters and parameters[self.RESOLUTION] is not None:
            resolution = self.parameterAsDouble(parameters, self.RESOLUTION, context)
            argv += ["--resolution", str(resolution)]
        layer_crs = crs_to_pyramids(self.parameterAsCrs(parameters, self.LAYER_CRS, context))
        if layer_crs:
            argv += ["--layer-crs", layer_crs]
        output_crs = crs_to_pyramids(self.parameterAsCrs(parameters, self.OUTPUT_CRS, context))
        if output_crs:
            argv += ["--output-crs", output_crs]
        resample = self.parameterAsString(parameters, self.RESAMPLE, context).strip()
        if resample:
            argv += ["--resample", resample]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
