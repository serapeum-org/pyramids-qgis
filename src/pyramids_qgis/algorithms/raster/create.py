"""Create a new, value-filled raster from scratch — wraps ``pyramids raster create``.

Builds a raster of a given size, dtype and band count. The grid is georeferenced from a
top-left corner plus a square cell size (a north-up grid); the full six-parameter affine
(``--geo``) is not exposed here — use the library directly for a rotated/sheared transform.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterPoint,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm


class RasterCreate(PyramidsAlgorithm):
    """Create a new raster of a given size, dtype and band count, filled with a value."""

    ROWS = "ROWS"
    COLUMNS = "COLUMNS"
    DTYPE = "DTYPE"
    BANDS = "BANDS"
    CELL_SIZE = "CELL_SIZE"
    TOP_LEFT = "TOP_LEFT"
    EPSG = "EPSG"
    NODATA = "NODATA"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_create"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Create raster"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Create a new raster from scratch, via pyramids: give its rows, columns, numpy dtype "
            "and band count. Georeference it by a top-left corner and a square cell size, set the "
            "CRS by EPSG code, and stamp a no-data value. The full six-parameter affine (--geo) "
            "is not exposed; use the library for a rotated grid."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ROWS, "Rows", type=QgsProcessingParameterNumber.Integer, defaultValue=1,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.COLUMNS, "Columns", type=QgsProcessingParameterNumber.Integer, defaultValue=1,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(self.DTYPE, "Numpy dtype (e.g. float32)",
                                         defaultValue="float32")
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BANDS, "Bands", type=QgsProcessingParameterNumber.Integer, defaultValue=1,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.CELL_SIZE, "Cell size (square pixel, optional)",
                type=QgsProcessingParameterNumber.Double, optional=True, minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterPoint(self.TOP_LEFT, "Top-left corner (optional)", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.EPSG, "EPSG code of the CRS (optional)",
                type=QgsProcessingParameterNumber.Integer, optional=True, minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NODATA, "No-data value (optional)",
                type=QgsProcessingParameterNumber.Double, optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Output raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster create`` command."""
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        rows = self.parameterAsInt(parameters, self.ROWS, context)
        columns = self.parameterAsInt(parameters, self.COLUMNS, context)
        dtype = self.parameterAsString(parameters, self.DTYPE, context).strip()
        if not dtype:
            raise QgsProcessingException("A numpy dtype is required.")
        bands = self.parameterAsInt(parameters, self.BANDS, context)

        argv = [
            "raster", "create", out,
            "--rows", str(rows), "--columns", str(columns),
            "--dtype", dtype, "--bands", str(bands),
        ]

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
