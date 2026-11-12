"""Extract a container raster's subdataset — wraps ``pyramids raster subdataset``.

NetCDF / HDF (and similar) containers hold several rasters addressed by a 0-based index or
a full subdataset name; this pulls one out into a standalone raster file.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path


class RasterSubdataset(PyramidsAlgorithm):
    """Extract one subdataset of a container raster (NetCDF/HDF, …) into its own file."""

    INPUT = "INPUT"
    KEY = "KEY"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_subdataset"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Extract subdataset"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Pull one subdataset out of a container raster (NetCDF, HDF, …) and write it to a "
            "standalone file. Identify the subdataset by its 0-based index (negatives allowed) "
            "or its full subdataset name, via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input container raster"))
        self.addParameter(QgsProcessingParameterString(self.KEY, "Subdataset index or full name"))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Output raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster subdataset`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        key = self.parameterAsString(parameters, self.KEY, context).strip()
        if not key:
            raise QgsProcessingException("A subdataset index or name is required.")

        self.run_pyramids(["raster", "subdataset", src, key, out, "--overwrite"], feedback)
        return {self.OUTPUT: out}
