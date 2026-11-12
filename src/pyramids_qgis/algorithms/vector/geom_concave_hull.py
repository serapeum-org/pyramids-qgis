"""Concave hull of each geometry — wraps ``pyramids vector geom concave-hull``."""

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


class VectorGeomConcaveHull(PyramidsAlgorithm):
    """Compute the concave hull of each geometry."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    RATIO = "RATIO"
    ALLOW_HOLES = "ALLOW_HOLES"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_geom_concave_hull"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Concave hull of vector geometries"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Compute the concave hull of each geometry, via pyramids. The ratio (in [0, 1]) sets "
            "the hull's tightness: 0 is the loosest (nearest the convex hull) and 1 is the "
            "tightest. Enable 'Allow holes' to permit interior rings in the result."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RATIO,
                "Hull tightness ratio [0, 1]",
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
                minValue=0.0,
                maxValue=1.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ALLOW_HOLES, "Permit holes in the hull", defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Concave hull"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector geom concave-hull`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        ratio = self.parameterAsDouble(parameters, self.RATIO, context)
        argv = ["vector", "geom", "concave-hull", src, out, "--overwrite", "--ratio", str(ratio)]
        if self.parameterAsBool(parameters, self.ALLOW_HOLES, context):
            argv.append("--allow-holes")
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
