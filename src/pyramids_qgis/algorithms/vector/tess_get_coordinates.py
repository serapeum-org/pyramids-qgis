"""Export a vector's coordinates to CSV — wraps ``pyramids vector tess get-coordinates``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorTessGetCoordinates(PyramidsAlgorithm):
    """Extract a vector layer's vertex coordinates and write them to a CSV file."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_tess_get_coordinates"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Get coordinates (to CSV)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Extract the vertex coordinates of a vector layer and write them to a CSV file, via "
            "pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT, "Output coordinates", fileFilter="CSV (*.csv)"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector tess get-coordinates`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        argv = ["vector", "tess", "get-coordinates", src, out, "--overwrite"]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
