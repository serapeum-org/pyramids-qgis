"""Dissolving self-union of a single vector — wraps ``pyramids vector overlay union-all``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path

#: Union algorithm choices, passed to ``--method``.
METHODS = ["unary", "coverage"]


class VectorOverlayUnionAll(PyramidsAlgorithm):
    """Merge all features of a single vector into one dissolved geometry."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    METHOD = "METHOD"
    GRID_SIZE = "GRID_SIZE"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_overlay_union_all"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Union (all, dissolve to one)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Union all features of a single vector into one merged geometry, via pyramids. The "
            "'unary' method is the general-purpose union; 'coverage' is faster for a clean, "
            "non-overlapping polygon coverage. An optional snapping grid size can be set to make "
            "the union robust to tiny coordinate noise. For a multi-layer source, a layer name or "
            "index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterEnum(self.METHOD, "Union method", options=METHODS, defaultValue=0)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.GRID_SIZE,
                "Snapping grid size (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Union (dissolved)"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector overlay union-all`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)

        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        method = METHODS[self.parameterAsEnum(parameters, self.METHOD, context)]
        argv = ["vector", "overlay", "union-all", src, out, "--method", method, "--overwrite"]
        if parameters.get(self.GRID_SIZE) is not None:
            argv += [
                "--grid-size",
                str(self.parameterAsDouble(parameters, self.GRID_SIZE, context)),
            ]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
