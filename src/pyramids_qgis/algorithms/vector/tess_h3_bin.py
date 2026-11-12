"""Bin a vector onto the H3 grid — wraps ``pyramids vector tess h3-bin``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorTessH3Bin(PyramidsAlgorithm):
    """Aggregate a vector layer's features into H3 cells at a given resolution."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    RESOLUTION = "RESOLUTION"
    AGG = "AGG"
    COLUMN = "COLUMN"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_tess_h3_bin"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "H3 bin (aggregate)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Bin a vector layer into H3 hexagonal cells and aggregate the features that fall in "
            "each one, via pyramids. The resolution runs from 0 (coarsest) to 15 (finest). By "
            "default each cell carries a feature count; give a numeric column and a reducer to "
            "aggregate that column instead. For a multi-layer source, a layer name or index may "
            "be selected."
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
                self.COLUMN, "Numeric column to aggregate (optional; default count)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.AGG, "Per-cell reducer applied to the column (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "H3 bins"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector tess h3-bin`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        resolution = str(self.parameterAsInt(parameters, self.RESOLUTION, context))
        argv = ["vector", "tess", "h3-bin", src, out, "--resolution", resolution, "--overwrite"]
        column = self.parameterAsString(parameters, self.COLUMN, context).strip()
        if column:
            argv += ["--column", column]
        agg = self.parameterAsString(parameters, self.AGG, context).strip()
        if agg:
            argv += ["--agg", agg]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
