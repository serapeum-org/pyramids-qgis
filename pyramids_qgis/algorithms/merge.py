"""Mosaic several rasters into one — wraps ``pyramids merge``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterRasterDestination,
)

from .base import PyramidsAlgorithm, layer_source_path, validate_input_path


class MergeRasters(PyramidsAlgorithm):
    """Merge (mosaic) two or more rasters into a single raster."""

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "merge"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Merge rasters (mosaic)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return "Mosaic two or more rasters into one file, via pyramids."

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.INPUT, "Input rasters (two or more)", layerType=QgsProcessing.TypeRaster
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT, "Merged raster")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids merge`` command."""
        layers = self.parameterAsLayerList(parameters, self.INPUT, context)
        if not layers or len(layers) < 2:
            raise QgsProcessingException("Merge needs at least two input rasters.")
        sources = []
        for layer in layers:
            path = layer_source_path(layer)
            validate_input_path(path, feedback)
            sources.append(path)

        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        self.run_pyramids(["merge", *sources, out, "--overwrite"], feedback)
        return {self.OUTPUT: out}
