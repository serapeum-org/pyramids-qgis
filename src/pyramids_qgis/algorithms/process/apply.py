"""Apply one registered tool to an input — wraps ``pyramids process apply``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, validate_input_path


class ProcessApply(PyramidsAlgorithm):
    """Run a single registered processing tool over one input raster or vector."""

    GROUP_LABEL = "Process"
    GROUP_ID = "process"

    TOOL = "NAME"  # parameter key kept as "NAME"; constant renamed off `name()` (Sonar S1845)
    INPUT = "INPUT"
    PARAMS = "PARAMS"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "process_apply"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Apply processing tool"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Run one registered processing tool over a single input raster or vector. Give the "
            "tool name (see 'pyramids process tool list'), the source, and the destination. Tool "
            "parameters are space-separated KEY=VALUE pairs (see 'pyramids process tool show "
            "NAME'), via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterString(self.TOOL, "Tool name"))
        self.addParameter(QgsProcessingParameterFile(self.INPUT, "Input raster or vector"))
        self.addParameter(
            QgsProcessingParameterString(
                self.PARAMS,
                "Tool parameters (optional; space-separated KEY=VALUE pairs)",
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterFileDestination(self.OUTPUT, "Output"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids process apply`` command."""
        tool = self.parameterAsString(parameters, self.TOOL, context).strip()
        if not tool:
            raise QgsProcessingException("A tool name is required.")

        src = self.parameterAsFile(parameters, self.INPUT, context)
        if not src:
            raise QgsProcessingException("An input path is required.")
        validate_input_path(src, feedback)
        out = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        argv = ["process", "apply", tool, src, out]
        for pair in self.parameterAsString(parameters, self.PARAMS, context).split():
            argv += ["--set", pair]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
