"""Vectorize a raster to GeoJSON — wraps ``pyramids shapes``.

pyramids ``shapes`` emits **one feature per cell** (a square polygon, or a centre point),
each carrying the band value. It is not a region-dissolving polygonizer, so it refuses very
large rasters unless explicitly allowed. Output is written as GeoJSON.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterVectorDestination,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path

#: Per-cell geometry options, passed to ``--geometry``.
GEOMETRY = ["polygon", "point"]


class Polygonize(PyramidsAlgorithm):
    """Convert a raster to a vector layer with one feature per cell (written as GeoJSON)."""

    INPUT = "INPUT"
    GEOMETRY = "GEOMETRY"
    ALLOW_LARGE = "ALLOW_LARGE"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "polygonize"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Polygonize raster (one feature per cell)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Vectorize a raster to GeoJSON, emitting one polygon (or point) per cell carrying "
            "the band value. This is not a region-dissolving polygonizer; above ~4 million "
            "cells it refuses unless 'Allow large rasters' is enabled. The output is written "
            "as GeoJSON regardless of the chosen file extension."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterEnum(
                self.GEOMETRY, "Per-cell geometry", options=GEOMETRY, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ALLOW_LARGE, "Allow large rasters (>~4M cells)", defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT, "Vectorized output (GeoJSON)", defaultValue=None
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids shapes`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        geometry = GEOMETRY[self.parameterAsEnum(parameters, self.GEOMETRY, context)]
        # Force the GeoJSON driver so the output content matches what QGIS loads back,
        # independent of the file extension the destination picks.
        argv = ["shapes", src, out, "--geometry", geometry, "--driver", "geojson", "--overwrite"]
        if self.parameterAsBool(parameters, self.ALLOW_LARGE, context):
            argv.append("--allow-large")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
