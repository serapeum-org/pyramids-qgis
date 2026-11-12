"""Simplify geometries (Douglas-Peucker) — wraps ``pyramids vector geom simplify``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorGeomSimplify(PyramidsAlgorithm):
    """Simplify every geometry with the Douglas-Peucker algorithm."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    TOLERANCE = "TOLERANCE"
    NO_PRESERVE_TOPOLOGY = "NO_PRESERVE_TOPOLOGY"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_geom_simplify"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Simplify vector geometries"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Simplify every geometry by Douglas-Peucker, via pyramids. Vertices that deviate by "
            "less than the tolerance (in the input vector's CRS units) are removed. By default "
            "topology is preserved; allowing it to change is faster but may produce invalid or "
            "self-intersecting geometries."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TOLERANCE,
                "Simplify tolerance",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.NO_PRESERVE_TOPOLOGY, "Allow topology to change (faster)", defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Simplified vector"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector geom simplify`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        tolerance = self.parameterAsDouble(parameters, self.TOLERANCE, context)
        argv = ["vector", "geom", "simplify", src, out, "--overwrite"]
        argv += ["--tolerance", str(tolerance)]
        if self.parameterAsBool(parameters, self.NO_PRESERVE_TOPOLOGY, context):
            argv.append("--no-preserve-topology")
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
