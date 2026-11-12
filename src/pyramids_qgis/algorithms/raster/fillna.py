"""Fill a raster's gaps with a constant — wraps ``pyramids raster fillna``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterFillna(PyramidsAlgorithm):
    """Replace every no-data gap in a raster with a constant value."""

    INPUT = "INPUT"
    VALUE = "VALUE"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_fillna"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Fill no-data gaps (constant)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return "Write a constant value into every no-data gap of a raster, via pyramids."

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.VALUE, "Fill value", type=QgsProcessingParameterNumber.Double
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Filled raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster fillna`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        value = self.parameterAsDouble(parameters, self.VALUE, context)
        # Join with '=' so a negative fill value is never mistaken for an option by argparse.
        self.run_pyramids(
            ["raster", "fillna", src, out, f"--value={value}", "--overwrite"], feedback
        )
        return {self.OUTPUT: out}
