"""Index a vector onto the H3 grid — wraps ``pyramids vector tess to-h3``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorTessToH3(PyramidsAlgorithm):
    """Convert a vector layer to the H3 cells that cover it at a given resolution."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    RESOLUTION = "RESOLUTION"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_tess_to_h3"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "To H3 cells"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Convert a vector layer into the H3 hexagonal cells that cover it, via pyramids. "
            "The resolution runs from 0 (coarsest) to 15 (finest). For a multi-layer source, "
            "a layer name or index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RESOLUTION,
                "H3 resolution (0 coarsest – 15 finest)",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=8,
                minValue=0,
                maxValue=15,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "H3 cells"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector tess to-h3`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        resolution = self.parameterAsInt(parameters, self.RESOLUTION, context)
        argv = ["vector", "tess", "to-h3", src, out, "--resolution", str(resolution), "--overwrite"]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
