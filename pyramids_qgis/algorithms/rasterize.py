"""Burn a vector layer into a new raster — wraps ``pyramids rasterize``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorLayer,
)

from .base import PyramidsAlgorithm, layer_source_path, validate_input_path


class Rasterize(PyramidsAlgorithm):
    """Rasterize a vector layer, either at a cell size or onto a template raster's grid."""

    INPUT = "INPUT"
    CELL_SIZE = "CELL_SIZE"
    TEMPLATE = "TEMPLATE"
    COLUMN = "COLUMN"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "rasterize"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Rasterize (vector to raster)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Burn a vector layer into a new raster. Give a cell size, or a template raster "
            "whose grid and CRS the output adopts (the template wins if both are set). "
            "Optionally burn a single attribute column; otherwise all non-geometry columns "
            "are burned."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.CELL_SIZE,
                "Cell size (output units)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.TEMPLATE, "Template raster (grid/CRS)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.COLUMN,
                "Attribute column to burn",
                parentLayerParameterName=self.INPUT,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT, "Rasterized output")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids rasterize`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        template_layer = self.parameterAsRasterLayer(parameters, self.TEMPLATE, context)
        cell_size = self.parameterAsDouble(parameters, self.CELL_SIZE, context)
        has_cell_size = self.CELL_SIZE in parameters and parameters[self.CELL_SIZE] is not None

        argv = ["rasterize", src, out]
        if template_layer is not None:
            template_path = layer_source_path(template_layer)
            validate_input_path(template_path, feedback)
            argv += ["--like", template_path]
        elif has_cell_size and cell_size > 0:
            argv += ["--cell-size", str(cell_size)]
        else:
            raise QgsProcessingException(
                "Provide a cell size or a template raster to define the output grid."
            )

        column = self.parameterAsString(parameters, self.COLUMN, context).strip()
        if column:
            argv += ["--column", column]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
