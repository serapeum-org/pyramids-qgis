"""Select a single time step from a NetCDF cube — wraps ``pyramids nc sel``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, validate_input_path


class NcSel(PyramidsAlgorithm):
    """Select one step on the time axis of a NetCDF cube by its date label."""

    GROUP_LABEL = "NetCDF"
    GROUP_ID = "nc"

    INPUT = "INPUT"
    TIME = "TIME"
    VAR = "VAR"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "nc_sel"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Select NetCDF time step"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Select a single step on the time axis by its date label (e.g. 2020-06-15); run "
            "'nc info' to see the step count and endpoints. Optionally narrow to one variable "
            "first. A '.nc' output keeps the result a NetCDF, via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterFile(self.INPUT, "Input NetCDF", extension="nc"))
        self.addParameter(QgsProcessingParameterString(self.TIME, "Time label (e.g. 2020-06-15)"))
        self.addParameter(
            QgsProcessingParameterString(
                self.VAR, "Variable to narrow to (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT, "Output NetCDF", fileFilter="NetCDF (*.nc)"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids nc sel`` command."""
        src = self.parameterAsFile(parameters, self.INPUT, context)
        validate_input_path(src, feedback)
        out = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        time = self.parameterAsString(parameters, self.TIME, context).strip()
        if not time:
            raise QgsProcessingException("A time label is required.")

        argv = ["nc", "sel", src, out, "--time", time]
        var = self.parameterAsString(parameters, self.VAR, context).strip()
        if var:
            argv += ["--var", var]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
