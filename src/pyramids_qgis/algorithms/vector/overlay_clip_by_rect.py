"""Clip a vector to a rectangle — wraps ``pyramids vector overlay clip-by-rect``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterExtent,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorOverlayClipByRect(PyramidsAlgorithm):
    """Clip a vector to a rectangular window, keeping only what falls inside it."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    EXTENT = "EXTENT"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_overlay_clip_by_rect"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Clip by rectangle (overlay)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Clip a vector to a rectangular window, via pyramids: only the geometry inside the "
            "rectangle is kept. The rectangle is interpreted in the input vector's CRS. For a "
            "multi-layer source, a layer name or index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(QgsProcessingParameterExtent(self.EXTENT, "Clip rectangle"))
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Clipped vector"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector overlay clip-by-rect`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)

        extent = self.parameterAsExtent(parameters, self.EXTENT, context, layer.crs())
        if extent.isNull():
            raise QgsProcessingException("A clip rectangle is required.")

        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["vector", "overlay", "clip-by-rect", src, out]
        argv += [
            "--rect",
            str(extent.xMinimum()),
            str(extent.yMinimum()),
            str(extent.xMaximum()),
            str(extent.yMaximum()),
        ]
        argv.append("--overwrite")
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
