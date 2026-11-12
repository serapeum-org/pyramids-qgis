"""Interpolate point values onto a raster — wraps ``pyramids vector tess interpolate-to-raster``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterExtent,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorTessInterpolateToRaster(PyramidsAlgorithm):
    """Interpolate a numeric point column onto a regular raster grid (IDW)."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    COLUMN = "COLUMN"
    METHOD = "METHOD"
    CELL_SIZE = "CELL_SIZE"
    BOUNDS = "BOUNDS"
    POWER = "POWER"
    N_NEIGHBORS = "N_NEIGHBORS"
    NODATA = "NODATA"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_tess_interpolate_to_raster"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Interpolate to raster (IDW)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Interpolate a numeric column of a point layer onto a regular raster grid (GeoTIFF) "
            "using inverse-distance weighting, via pyramids. Optionally set the output pixel "
            "size, extent, IDW distance exponent, neighbour count and NoData value; the extent "
            "defaults to the points' total bounds. For a multi-layer source, a layer name or "
            "index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector (points)"))
        self.addParameter(
            QgsProcessingParameterString(self.COLUMN, "Numeric column to interpolate")
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.METHOD, "Interpolation method (optional; only idw)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.CELL_SIZE,
                "Output pixel size (CRS units, optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterExtent(self.BOUNDS, "Output extent (optional)", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.POWER,
                "IDW distance exponent (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.N_NEIGHBORS,
                "Nearest-neighbour count (optional)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NODATA,
                "NoData value for un-interpolable cells (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT, "Interpolated raster")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector tess interpolate-to-raster`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        column = self.parameterAsString(parameters, self.COLUMN, context).strip()
        if not column:
            raise QgsProcessingException("A numeric column to interpolate is required.")

        argv = ["vector", "tess", "interpolate-to-raster", src, out, "--column", column]
        method = self.parameterAsString(parameters, self.METHOD, context).strip()
        if method:
            argv += ["--method", method]
        if self.CELL_SIZE in parameters and parameters[self.CELL_SIZE] is not None:
            cell_size = self.parameterAsDouble(parameters, self.CELL_SIZE, context)
            argv += ["--cell-size", str(cell_size)]
        extent = self.parameterAsExtent(parameters, self.BOUNDS, context)
        if not extent.isNull():
            argv += [
                "--bounds",
                str(extent.xMinimum()),
                str(extent.yMinimum()),
                str(extent.xMaximum()),
                str(extent.yMaximum()),
            ]
        if self.POWER in parameters and parameters[self.POWER] is not None:
            argv += ["--power", str(self.parameterAsDouble(parameters, self.POWER, context))]
        if self.N_NEIGHBORS in parameters and parameters[self.N_NEIGHBORS] is not None:
            n_neighbors = self.parameterAsInt(parameters, self.N_NEIGHBORS, context)
            argv += ["--n-neighbors", str(n_neighbors)]
        if self.NODATA in parameters and parameters[self.NODATA] is not None:
            argv += ["--nodata", str(self.parameterAsDouble(parameters, self.NODATA, context))]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
