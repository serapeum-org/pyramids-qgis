"""Sample random points within geometries — wraps ``pyramids vector tess sample-points``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class VectorTessSamplePoints(PyramidsAlgorithm):
    """Sample a fixed number of points within each geometry of a vector layer."""

    GROUP_LABEL = "Vector"
    GROUP_ID = "vector"

    INPUT = "INPUT"
    SIZE = "SIZE"
    METHOD = "METHOD"
    SEED = "SEED"
    LAYER = "LAYER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "vector_tess_sample_points"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Sample points"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Sample a fixed number of points within each geometry of a vector layer, via "
            "pyramids. Optionally choose a sampling method and set a random seed for "
            "reproducibility. For a multi-layer source, a layer name or index may be selected."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT, "Input vector"))
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SIZE,
                "Points per geometry",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=100,
                minValue=1,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(self.METHOD, "Sampling method (optional)", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.SEED,
                "Random seed (optional)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.LAYER, "Layer name/index (optional; multi-layer sources)", optional=True
            )
        )
        self.addParameter(QgsProcessingParameterVectorDestination(self.OUTPUT, "Sample points"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids vector tess sample-points`` command."""
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        size = self.parameterAsInt(parameters, self.SIZE, context)
        argv = ["vector", "tess", "sample-points", src, out, "--size", str(size), "--overwrite"]
        method = self.parameterAsString(parameters, self.METHOD, context).strip()
        if method:
            argv += ["--method", method]
        if self.SEED in parameters and parameters[self.SEED] is not None:
            argv += ["--seed", str(self.parameterAsInt(parameters, self.SEED, context))]
        layer_ref = self.parameterAsString(parameters, self.LAYER, context).strip()
        if layer_ref:
            argv += ["--layer", layer_ref]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
