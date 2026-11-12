"""Keep a chosen subset of bands — wraps ``pyramids raster select-bands``.

Writes a new raster holding only the named bands, in the given order (duplicates allowed).
Bands are entered as 1-based indices, separated by spaces or commas.
"""

from __future__ import annotations

import re

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterSelectBands(PyramidsAlgorithm):
    """Write a raster keeping only a chosen subset of bands, in a chosen order."""

    INPUT = "INPUT"
    BANDS = "BANDS"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_select_bands"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Select bands"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Write a new raster keeping only the chosen bands, via pyramids. Enter 1-based band "
            "indices separated by spaces or commas, in the order you want them (duplicates are "
            "allowed), e.g. '3 2 1'."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterString(
                self.BANDS, "Bands to keep (1-based, space/comma separated)", defaultValue="1"
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Output raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster select-bands`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        raw = self.parameterAsString(parameters, self.BANDS, context).strip()
        tokens = [t for t in re.split(r"[,\s]+", raw) if t]
        if not tokens:
            raise QgsProcessingException("Provide at least one band index to keep.")
        for token in tokens:
            if not token.lstrip("+").isdigit():
                raise QgsProcessingException(f"Band indices must be integers; got {token!r}.")

        self.run_pyramids(
            ["raster", "select-bands", src, out, "--bands", *tokens, "--overwrite"], feedback
        )
        return {self.OUTPUT: out}
