"""Spatial join of two vectors — wraps ``pyramids vector overlay sjoin``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path

#: Join-type choices, passed to ``--how``.
HOWS = ["inner", "left", "right"]
#: Spatial-predicate choices, passed to ``--predicate``.
PREDICATES = [
    "intersects",
    "contains",
    "within",
    "covers",
    "covered_by",
    "crosses",
    "overlaps",
    "touches",
]


class VectorOverlaySjoin(PyramidsAlgorithm):
    """Attach attributes from a right-hand vector by a spatial predicate."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    RIGHT = "RIGHT"
    HOW = "HOW"
    PREDICATE = "PREDICATE"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_overlay_sjoin"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Spatial join"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Spatially join two vectors, via pyramids: each source feature gains the attributes "
            "of the right-hand features that satisfy the chosen spatial predicate (intersects, "
            "contains, within, ...). The join type (inner / left / right) controls which "
            "unmatched features are kept. For a multi-layer source, a layer name or index may be "
            "selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector (left)"))
        self.addParameter(QgsProcessingParameterVectorLayer(self.RIGHT, "Right-hand vector"))
        self.addParameter(
            QgsProcessingParameterEnum(self.HOW, "Join type", options=HOWS, defaultValue=0)
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.PREDICATE, "Spatial predicate", options=PREDICATES, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Joined vector"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector overlay sjoin`` command."""
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
        predicate = PREDICATES[self.parameterAsEnum(parameters, self.PREDICATE, context)]
        argv = ["vector", "overlay", "sjoin", src, out, "--right", right]
        argv += ["--how", how, "--predicate", predicate, "--overwrite"]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
