"""Smallest enclosing circle — wraps ``pyramids vector geom minimum-bounding-circle``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorGeomMinimumBoundingCircle(PyramidsAlgorithm):
    """Compute the smallest circle enclosing each geometry."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_geom_minimum_bounding_circle"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Minimum bounding circle of vector geometries"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Compute the smallest circle that fully encloses each geometry, via pyramids. Each "
            "output feature is the polygonal minimum bounding circle of the corresponding input "
            "geometry."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorDestination(self.OUTPUT, "Minimum bounding circles")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector geom minimum-bounding-circle`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["vector", "geom", "minimum-bounding-circle", src, out, "--overwrite"]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
