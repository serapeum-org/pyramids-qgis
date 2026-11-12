"""Extract one NetCDF variable to a GDAL raster — wraps ``pyramids nc extract``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterFile,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, validate_input_path


class NcExtract(PyramidsAlgorithm):
    """Extract a single variable from a NetCDF cube into a GDAL raster."""

    GROUP_LABEL = "NetCDF"
    GROUP_ID = "nc"

    INPUT = "INPUT"
    VAR = "VAR"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "nc_extract"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Extract NetCDF variable to raster"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Extract one variable from a NetCDF cube to a GDAL raster. The variable name may be "
            "qualified with its group ('group/var'). The output format follows the destination "
            "file extension, via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterFile(self.INPUT, "Input NetCDF", extension="nc"))
        self.addParameter(
            QgsProcessingParameterString(self.VAR, "Variable name (supports 'group/var')")
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Extracted raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids nc extract`` command."""
        src = self.parameterAsFile(parameters, self.INPUT, context)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        var = self.parameterAsString(parameters, self.VAR, context).strip()
        if not var:
            raise QgsProcessingException("A variable name is required.")

        self.run_pyramids(
            ["nc", "extract", src, out, "--var", var, "--overwrite"],
            feedback,
        )
        return {self.OUTPUT: out}
