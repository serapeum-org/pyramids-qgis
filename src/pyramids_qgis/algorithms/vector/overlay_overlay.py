"""General spatial overlay of two vectors — wraps ``pyramids vector overlay overlay``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path

#: Overlay-mode choices, passed to ``--how``.
HOWS = ["intersection", "union", "identity", "symmetric_difference", "difference"]


class VectorOverlayOverlay(PyramidsAlgorithm):
    """Overlay two vectors with a selectable set-theoretic mode."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    RIGHT = "RIGHT"
    HOW = "HOW"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_overlay_overlay"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Overlay (general)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Overlay two vectors with a selectable set-theoretic mode, via pyramids: "
            "intersection, union, identity, symmetric difference, or difference. For a "
            "multi-layer source, a layer name or index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(QgsProcessingParameterVectorLayer(self.RIGHT, "Right-hand vector"))
        self.addParameter(
            QgsProcessingParameterEnum(self.HOW, "Overlay mode", options=HOWS, defaultValue=0)
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Overlay"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector overlay overlay`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)

        right_layer = self.parameterAsVectorLayer(parameters, self.RIGHT, context)
        if right_layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.RIGHT))
        right = layer_source_path(right_layer)
        validate_input_path(right, feedback)

        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        how = HOWS[self.parameterAsEnum(parameters, self.HOW, context)]
        argv = ["vector", "overlay", "overlay", src, out, "--right", right, "--how", how]
        argv.append("--overwrite")
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
