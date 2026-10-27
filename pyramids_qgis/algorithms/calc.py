"""Evaluate a band expression over aligned rasters — wraps ``pyramids calc``.

The inputs are bound to ``A``, ``B``, ``C`` ... in the order they are given, matching the
pyramids CLI. Every input must already sit on the first input's grid (pyramids ``calc``
does not resample). The expression is evaluated by a safe AST whitelist in pyramids — only
arithmetic over the bands, comparisons, and a small set of ``np.<func>`` calls.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterString,
)

from .base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterCalc(PyramidsAlgorithm):
    """Raster calculator: evaluate an expression over A, B, C ... into a new raster."""

    INPUT = "INPUT"
    EXPRESSION = "EXPRESSION"
    DTYPE = "DTYPE"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "calc"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Raster calculator"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Evaluate a band expression over the input rasters, bound to A, B, C ... in "
            "order. Example (NDVI): (B - A) / (B + A) with A=red, B=NIR. Inputs must share "
            "the first input's grid; pyramids does not resample. Allowed: arithmetic, "
            "comparisons, and np.where / np.clip / np.log / np.sqrt / np.minimum / ..."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.INPUT, "Input rasters (A, B, C ...)", layerType=QgsProcessing.TypeRaster
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.EXPRESSION, "Expression", defaultValue="(B - A) / (B + A)"
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DTYPE, "Output dtype (optional, e.g. float32)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT, "Result raster")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids calc`` command."""
        layers = self.parameterAsLayerList(parameters, self.INPUT, context)
        if not layers:
            raise QgsProcessingException("Raster calculator needs at least one input raster.")
        if len(layers) > 26:
            raise QgsProcessingException("Raster calculator supports at most 26 inputs (A..Z).")
        sources = []
        for layer in layers:
            path = layer_source_path(layer)
            validate_input_path(path, feedback)
            sources.append(path)

        expression = self.parameterAsString(parameters, self.EXPRESSION, context).strip()
        if not expression:
            raise QgsProcessingException("An expression is required.")
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        argv = ["calc", expression, *sources, out, "--overwrite"]
        dtype = self.parameterAsString(parameters, self.DTYPE, context).strip()
        if dtype:
            argv += ["--dtype", dtype]

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
