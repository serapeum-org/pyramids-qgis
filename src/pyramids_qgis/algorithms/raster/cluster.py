"""Label connected cells within a value range — wraps ``pyramids raster cluster``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterCluster(PyramidsAlgorithm):
    """Label connected groups of cells whose values fall within a given range."""

    INPUT = "INPUT"
    LOWER = "LOWER"
    UPPER = "UPPER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_cluster"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Cluster (label value range)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Label connected groups of cells whose values fall within [lower, upper] into a "
            "label raster, via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.LOWER, "Lower bound", type=QgsProcessingParameterNumber.Double
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.UPPER, "Upper bound", type=QgsProcessingParameterNumber.Double
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Label raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster cluster`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        lower = self.parameterAsDouble(parameters, self.LOWER, context)
        upper = self.parameterAsDouble(parameters, self.UPPER, context)
        # Join numeric bounds with '=' so a negative value is never mistaken for an option by
        # argparse's negative-number heuristic.
        self.run_pyramids(
            ["raster", "cluster", src, out, f"--lower={lower}", f"--upper={upper}", "--overwrite"],
            feedback,
        )
        return {self.OUTPUT: out}
