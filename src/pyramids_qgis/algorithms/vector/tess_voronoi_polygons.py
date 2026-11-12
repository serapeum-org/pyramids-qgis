"""Voronoi tessellation of a vector's vertices — wraps ``pyramids vector tess voronoi-polygons``."""

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


class VectorTessVoronoiPolygons(PyramidsAlgorithm):
    """Build the Voronoi tessellation of a vector layer's vertices."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    TOLERANCE = "TOLERANCE"
    ONLY_EDGES = "ONLY_EDGES"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_tess_voronoi_polygons"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Voronoi polygons"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Build the Voronoi tessellation of a vector layer's vertices, via pyramids. "
            "Optionally snap input coordinates to a grid first, or return the tessellation "
            "edges as lines instead of polygons. For a multi-layer source, a layer name or "
            "index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TOLERANCE,
                "Snap tolerance (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ONLY_EDGES, "Return edges as lines", defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Voronoi polygons"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector tess voronoi-polygons`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["vector", "tess", "voronoi-polygons", src, out, "--overwrite"]
        if self.TOLERANCE in parameters and parameters[self.TOLERANCE] is not None:
            tolerance = self.parameterAsDouble(parameters, self.TOLERANCE, context)
            argv += ["--tolerance", str(tolerance)]
        if self.parameterAsBool(parameters, self.ONLY_EDGES, context):
            argv.append("--only-edges")
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
