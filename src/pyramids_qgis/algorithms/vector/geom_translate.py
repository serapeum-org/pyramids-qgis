"""Shift geometries by an offset — wraps ``pyramids vector geom translate``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorGeomTranslate(PyramidsAlgorithm):
    """Shift every geometry by a per-axis offset."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    XOFF = "XOFF"
    YOFF = "YOFF"
    ZOFF = "ZOFF"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_geom_translate"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Translate vector geometries"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Shift every geometry by a per-axis offset, via pyramids. The offsets are in the input "
            "vector's CRS units; a negative offset shifts in the opposite direction."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.XOFF, "X offset", type=QgsProcessingParameterNumber.Double, defaultValue=0.0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.YOFF, "Y offset", type=QgsProcessingParameterNumber.Double, defaultValue=0.0
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ZOFF, "Z offset", type=QgsProcessingParameterNumber.Double, defaultValue=0.0
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Translated vector"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector geom translate`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        xoff = self.parameterAsDouble(parameters, self.XOFF, context)
        yoff = self.parameterAsDouble(parameters, self.YOFF, context)
        zoff = self.parameterAsDouble(parameters, self.ZOFF, context)
        # '=' join keeps a negative offset from being parsed as an option rather than a value.
        argv = ["vector", "geom", "translate", src, out, "--overwrite"]
        argv += [f"--xoff={xoff}", f"--yoff={yoff}", f"--zoff={zoff}"]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
