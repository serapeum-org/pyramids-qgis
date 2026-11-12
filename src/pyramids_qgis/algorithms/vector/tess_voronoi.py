"""Voronoi diagram of points, optionally clipped — wraps ``pyramids vector tess voronoi``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorTessVoronoi(PyramidsAlgorithm):
    """Build a Voronoi diagram of a point layer, optionally clipped to a boundary."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    VALUES = "VALUES"
    CLIP = "CLIP"
    DRIVER = "DRIVER"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_tess_voronoi"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Voronoi diagram"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Build a Voronoi diagram over a point layer, via pyramids. Optionally copy a column "
            "onto each cell for a choropleth, clip the cells to a boundary vector, and pick the "
            "output OGR driver. For a multi-layer source, a layer name or index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector (points)"))
        self.addParameter(
            QgsProcessingParameterString(
                self.VALUES, "Column copied onto each cell (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.CLIP, "Boundary vector to clip cells to (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DRIVER, "Driver (optional; default: from extension)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Voronoi diagram"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector tess voronoi`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["vector", "tess", "voronoi", src, out, "--overwrite"]
        values = self.parameterAsString(parameters, self.VALUES, context).strip()
        if values:
            argv += ["--values", values]
        clip_layer = self.parameterAsVectorLayer(parameters, self.CLIP, context)
        if clip_layer is not None:
            clip_path = layer_source_path(clip_layer)
            validate_input_path(clip_path, feedback)
            argv += ["--clip", clip_path]
        driver = self.parameterAsString(parameters, self.DRIVER, context).strip()
        if driver:
            argv += ["--driver", driver]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
