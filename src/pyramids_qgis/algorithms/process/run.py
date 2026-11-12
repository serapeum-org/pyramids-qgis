"""Run a processing pipeline over an input — wraps ``pyramids process run``.

The pipeline YAML lists a sequence of registered tools; it is applied to the input and the
result is written into the output *directory* (one file per input), so the output is modelled
as a folder destination.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
)

from ..base import PyramidsAlgorithm, validate_input_path

#: Error policies forwarded verbatim to ``--on-error``; indices are stable, default ``skip``.
ON_ERROR = ["skip", "raise"]


class ProcessRun(PyramidsAlgorithm):
    """Apply a declarative processing pipeline (YAML) to an input."""

    GROUP_LABEL = "Process"
    GROUP_ID = "process"

    PIPELINE = "PIPELINE"
    INPUT = "INPUT"
    ON_ERROR = "ON_ERROR"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "process_run"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Run processing pipeline"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Run a declarative processing pipeline (a YAML listing a sequence of registered "
            "tools) over an input raster or vector. The result is written into the output "
            "directory. The error policy decides whether a failing step is skipped or raised, "
            "via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterFile(self.PIPELINE, "Pipeline YAML"))
        self.addParameter(QgsProcessingParameterFile(self.INPUT, "Input raster or vector"))
        self.addParameter(
            QgsProcessingParameterEnum(
                self.ON_ERROR, "Error policy", options=ON_ERROR, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(self.OUTPUT, "Output (directory)")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids process run`` command."""
        pipeline = self.parameterAsFile(parameters, self.PIPELINE, context)
        if not pipeline:
            raise QgsProcessingException("A pipeline YAML file is required.")
        validate_input_path(pipeline, feedback)

        src = self.parameterAsFile(parameters, self.INPUT, context)
        if not src:
            raise QgsProcessingException("An input path is required.")
        validate_input_path(src, feedback)
        out = self.parameterAsString(parameters, self.OUTPUT, context)

        on_error = ON_ERROR[self.parameterAsEnum(parameters, self.ON_ERROR, context)]
        self.run_pyramids(
            [
                "process",
                "run",
                pipeline,
                "--inputs",
                src,
                "--out",
                out,
                "--on-error",
                on_error,
            ],
            feedback,
        )
        return {self.OUTPUT: out}
