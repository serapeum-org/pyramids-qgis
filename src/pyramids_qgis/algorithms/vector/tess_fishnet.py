"""Generate a regular grid of square cells — wraps ``pyramids vector tess fishnet``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterCrs,
    QgsProcessingParameterExtent,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorDestination,
)

from ..base import PyramidsAlgorithm


class VectorTessFishnet(PyramidsAlgorithm):
    """Generate a fishnet: a regular grid of square polygons over an extent."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    BOUNDS = "BOUNDS"
    CELL_SIZE = "CELL_SIZE"
    CRS = "CRS"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_tess_fishnet"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Fishnet grid"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Generate a fishnet: a regular grid of square polygons covering the given extent at "
            "a chosen cell size, via pyramids. This algorithm takes no input layer; the grid is "
            "built from the extent, cell size and CRS. The CRS must be an EPSG code, and the "
            "extent and cell size are interpreted in its units."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterExtent(self.BOUNDS, "Grid extent"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.CELL_SIZE,
                "Cell size (CRS units)",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=1.0,
                minValue=0.0,
            )
        )
        self.addParameter(QgsProcessingParameterCrs(self.CRS, "Grid CRS (EPSG)"))
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Fishnet grid"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector tess fishnet`` command."""
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        crs = self.parameterAsCrs(parameters, self.CRS, context)
        if crs is None or not crs.isValid():
            raise QgsProcessingException("A valid grid CRS is required.")
        auth_id = crs.authid()
        if not auth_id or not auth_id.upper().startswith("EPSG:"):
            raise QgsProcessingException("The grid CRS must be an EPSG code.")
        epsg = auth_id.split(":", 1)[1]

        # Reproject the entered extent into the grid CRS so the bounds match --epsg's units.
        extent = self.parameterAsExtent(parameters, self.BOUNDS, context, crs)
        if extent.isNull():
            raise QgsProcessingException("A grid extent is required.")
        cell_size = self.parameterAsDouble(parameters, self.CELL_SIZE, context)

        argv = [
            "vector",
            "tess",
            "fishnet",
            out,
            "--bounds",
            str(extent.xMinimum()),
            str(extent.yMinimum()),
            str(extent.xMaximum()),
            str(extent.yMaximum()),
            "--cell-size",
            str(cell_size),
            "--epsg",
            epsg,
            "--overwrite",
        ]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
