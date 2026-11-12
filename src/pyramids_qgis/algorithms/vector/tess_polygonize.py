"""Polygonize noded lines into faces — wraps ``pyramids vector tess polygonize``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorTessPolygonize(PyramidsAlgorithm):
    """Assemble the polygonal faces enclosed by a vector layer's (noded) lines."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    FULL = "FULL"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_tess_polygonize"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Polygonize lines"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Assemble the polygonal faces enclosed by a vector layer's lines, via pyramids. "
            "Enable 'Report diagnostics' to also log cut/dangle/invalid counts. For a "
            "multi-layer source, a layer name or index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector (lines)"))
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.FULL, "Report cut/dangle/invalid counts", defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Polygonized faces"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector tess polygonize`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["vector", "tess", "polygonize", src, out, "--overwrite"]
        if self.parameterAsBool(parameters, self.FULL, context):
            argv.append("--full")
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
