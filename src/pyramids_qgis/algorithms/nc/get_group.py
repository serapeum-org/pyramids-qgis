"""Pull a sub-group out of a NetCDF cube — wraps ``pyramids nc get-group``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, validate_input_path


class NcGetGroup(PyramidsAlgorithm):
    """Extract a (possibly nested) sub-group of a NetCDF file into its own NetCDF."""

    GROUP_LABEL = "NetCDF"
    GROUP_ID = "nc"

    INPUT = "INPUT"
    GROUP = "GROUP"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "nc_get_group"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Extract NetCDF group"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Pull a sub-group out of a NetCDF cube and write it to its own file. The group name "
            "may be nested ('a/b'). A '.nc' output keeps the result a NetCDF, via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(
            QgsProcessingParameterFile(self.INPUT, "Input NetCDF", extension="nc")
        )
        self.addParameter(
            QgsProcessingParameterString(self.GROUP, "Sub-group name (nested 'a/b' accepted)")
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT, "Output NetCDF", fileFilter="NetCDF (*.nc)"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids nc get-group`` command."""
        src = self.parameterAsFile(parameters, self.INPUT, context)
        validate_input_path(src, feedback)
        out = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        group = self.parameterAsString(parameters, self.GROUP, context).strip()
        if not group:
            raise QgsProcessingException("A sub-group name is required.")

        self.run_pyramids(
            ["nc", "get-group", src, out, "--group", group, "--overwrite"],
            feedback,
        )
        return {self.OUTPUT: out}
