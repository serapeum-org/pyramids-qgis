"""Dissolve features by an attribute — wraps ``pyramids vector overlay dissolve``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorOverlayDissolve(PyramidsAlgorithm):
    """Merge features that share an attribute value into one geometry per group."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    BY = "BY"
    AGGFUNC = "AGGFUNC"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_overlay_dissolve"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Dissolve"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Dissolve a vector, via pyramids: merge features into one geometry per group. Give a "
            "'group by' column to dissolve within each distinct value of that column; omit it to "
            "merge everything into a single feature. An aggregation function (e.g. sum, mean, "
            "first) controls how the non-geometry columns are combined. For a multi-layer source, "
            "a layer name or index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterString(
                self.BY, "Group-by column (optional; default: dissolve all)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.AGGFUNC, "Aggregation for non-geometry columns (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Dissolved vector"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector overlay dissolve`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)

        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["vector", "overlay", "dissolve", src, out, "--overwrite"]
        by = self.parameterAsString(parameters, self.BY, context).strip()
        if by:
            argv += ["--by", by]
        aggfunc = self.parameterAsString(parameters, self.AGGFUNC, context).strip()
        if aggfunc:
            argv += ["--aggfunc", aggfunc]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
