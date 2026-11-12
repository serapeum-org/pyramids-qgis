"""Combine two aligned rasters element-wise — wraps ``pyramids raster combine``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path

#: Element-wise binary operations, passed to ``--op`` (order matches the pyramids CLI choices).
OPERATIONS = ["add", "divide", "maximum", "minimum", "multiply", "subtract"]


class RasterCombine(PyramidsAlgorithm):
    """Apply an element-wise binary operation to the matching cells of two rasters."""

    INPUT_A = "INPUT_A"
    INPUT_B = "INPUT_B"
    OP = "OP"
    BAND = "BAND"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_combine"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Combine rasters (element-wise)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Apply an element-wise binary operation (add, divide, maximum, minimum, multiply, "
            "subtract) to the matching cells of two rasters. The second raster must share the "
            "first's grid. Optionally restrict the operation to a single band, via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT_A, "First raster (A)"))
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT_B, "Second raster (B)"))
        self.addParameter(
            QgsProcessingParameterEnum(self.OP, "Operation", options=OPERATIONS, defaultValue=0)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BAND,
                "Band to combine (optional; default: every band)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Combined raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster combine`` command."""
        layer_a = self.parameterAsRasterLayer(parameters, self.INPUT_A, context)
        if layer_a is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT_A))
        a = layer_source_path(layer_a)
        validate_input_path(a, feedback)

        layer_b = self.parameterAsRasterLayer(parameters, self.INPUT_B, context)
        if layer_b is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT_B))
        b = layer_source_path(layer_b)
        validate_input_path(b, feedback)

        op = OPERATIONS[self.parameterAsEnum(parameters, self.OP, context)]
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["raster", "combine", a, b, out, "--op", op, "--overwrite"]
        if self.BAND in parameters and parameters[self.BAND] is not None:
            argv += ["--band", str(self.parameterAsInt(parameters, self.BAND, context))]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
