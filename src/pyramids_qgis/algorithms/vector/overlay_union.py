"""Geometric union of two vectors — wraps ``pyramids vector overlay union``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorOverlayUnion(PyramidsAlgorithm):
    """Combine two vectors, splitting geometries along their mutual boundaries."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    OTHER = "OTHER"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_overlay_union"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Union (overlay)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Compute the geometric union of two vectors, via pyramids: the output combines both "
            "inputs, splitting the geometries along their mutual boundaries and carrying the "
            "attributes of both. For a multi-layer source, a layer name or index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterVectorLayer(self.OTHER, "Second vector (right-hand operand)")
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Union"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector overlay union`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)

        other_layer = self.parameterAsVectorLayer(parameters, self.OTHER, context)
        if other_layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.OTHER))
        other = layer_source_path(other_layer)
        validate_input_path(other, feedback)

        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["vector", "overlay", "union", src, out, "--other", other, "--overwrite"]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
