"""Create a new empty raster from scratch — wraps ``pyramids raster create-empty``.

Like ``create`` but the bands/dtype/no-data fields carry library defaults, so only the size is
required. The grid is georeferenced from a top-left corner plus a square cell size (a north-up
grid); the full six-parameter affine (``--geo``) is not exposed here.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm


class RasterCreateEmpty(PyramidsAlgorithm):
    """Create a new empty raster of a given size (bands/dtype/no-data default from the library)."""

    ROWS = "ROWS"
    COLS = "COLS"
    BANDS = "BANDS"
    DTYPE = "DTYPE"
    CELL_SIZE = "CELL_SIZE"
    TOP_LEFT = "TOP_LEFT"
    EPSG = "EPSG"
    NODATA = "NODATA"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_create_empty"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Create empty raster"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Create a new empty raster from scratch, via pyramids: only the rows and columns are "
            "required (bands default to 1, dtype to float32, no-data to -9999). Georeference it "
            "by a top-left corner and a square cell size, set the CRS by EPSG code, and stamp a "
            "no-data value. The full six-parameter affine (--geo) is not exposed."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ROWS,
                "Rows",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=1,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.COLS,
                "Columns",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=1,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BANDS,
                "Bands (optional; default 1)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DTYPE, "Numpy dtype (optional; default float32)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.CELL_SIZE,
                "Cell size (square pixel, optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterPoint(self.TOP_LEFT, "Top-left corner (optional)", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.EPSG,
                "EPSG code of the CRS (optional)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NODATA,
                "No-data value (optional; default -9999)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Output raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster create-empty`` command."""
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        rows = self.parameterAsInt(parameters, self.ROWS, context)
        cols = self.parameterAsInt(parameters, self.COLS, context)

        argv = ["raster", "create-empty", out, "--rows", str(rows), "--cols", str(cols)]

        if self.BANDS in parameters and parameters[self.BANDS] is not None:
            argv += ["--bands", str(self.parameterAsInt(parameters, self.BANDS, context))]
        dtype = self.parameterAsString(parameters, self.DTYPE, context).strip()
        if dtype:
            argv += ["--dtype", dtype]
        if self.CELL_SIZE in parameters and parameters[self.CELL_SIZE] is not None:
            cell_size = self.parameterAsDouble(parameters, self.CELL_SIZE, context)
            if cell_size > 0:
                argv += ["--cell-size", str(cell_size)]
        if self.TOP_LEFT in parameters and parameters[self.TOP_LEFT]:
            top_left = self.parameterAsPoint(parameters, self.TOP_LEFT, context)
            argv += ["--top-left", str(top_left.x()), str(top_left.y())]
        if self.EPSG in parameters and parameters[self.EPSG] is not None:
            argv += ["--epsg", str(self.parameterAsInt(parameters, self.EPSG, context))]
        if self.NODATA in parameters and parameters[self.NODATA] is not None:
            nodata = self.parameterAsDouble(parameters, self.NODATA, context)
            # '=' join keeps a negative / scientific-notation sentinel from being parsed as an
            # option rather than this flag's value (review R2-L4).
            argv.append(f"--no-data-value={nodata}")

        argv.append("--overwrite")
        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
