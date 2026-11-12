"""Align a raster collection to a reference grid — wraps ``pyramids collection align``.

Every timestep is resampled onto the reference raster's grid/CRS and written out, so the output
is a *directory* holding one file per timestep.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, layer_source_path, validate_input_path
from ..raster.warp import RESAMPLING


class CollectionAlign(PyramidsAlgorithm):
    """Align every timestep of a raster collection to a reference raster's grid."""

    GROUP_LABEL = "Collection"
    GROUP_ID = "collection"

    INPUT = "INPUT"
    REFERENCE = "REFERENCE"
    RESAMPLING = "RESAMPLING"
    DATE_FORMAT = "DATE_FORMAT"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "collection_align"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Align raster collection (to reference grid)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Resample every timestep of a stack of co-registered rasters onto a reference "
            "raster's grid and CRS. One file per timestep is written into the output directory, "
            "via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT,
                "Input raster collection (directory)",
                behavior=QgsProcessingParameterFile.Folder,
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(self.REFERENCE, "Reference raster (grid to adopt)")
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.RESAMPLING, "Resampling method", options=RESAMPLING, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.DATE_FORMAT,
                "Filename date format (optional, e.g. %Y.%m.%d)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(self.OUTPUT, "Aligned collection (directory)")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids collection align`` command."""
        src = self.parameterAsFile(parameters, self.INPUT, context)
        validate_input_path(src, feedback)
        out = self.parameterAsString(parameters, self.OUTPUT, context)

        reference = self.parameterAsRasterLayer(parameters, self.REFERENCE, context)
        if reference is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.REFERENCE))
        ref_path = layer_source_path(reference)
        validate_input_path(ref_path, feedback)

        resampling = RESAMPLING[self.parameterAsEnum(parameters, self.RESAMPLING, context)]
        argv = [
            "collection",
            "align",
            src,
            out,
            "--reference",
            ref_path,
            "--resampling",
            resampling,
        ]

        date_format = self.parameterAsString(parameters, self.DATE_FORMAT, context).strip()
        if date_format:
            argv += ["--date-format", date_format]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
