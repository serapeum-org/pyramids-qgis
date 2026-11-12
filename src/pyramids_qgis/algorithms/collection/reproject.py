"""Reproject a raster collection to a target CRS — wraps ``pyramids collection reproject``.

Every timestep is reprojected to the target CRS and written out, so the output is a *directory*
holding one file per timestep.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterCrs,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterString,
)

from ..base import PyramidsAlgorithm, crs_to_pyramids, validate_input_path
from ..raster.warp import RESAMPLING


class CollectionReproject(PyramidsAlgorithm):
    """Reproject every timestep of a raster collection to a target CRS."""

    GROUP_LABEL = "Collection"
    GROUP_ID = "collection"

    INPUT = "INPUT"
    CRS = "CRS"
    RESAMPLING = "RESAMPLING"
    MAINTAIN_ALIGNMENT = "MAINTAIN_ALIGNMENT"
    DATE_FORMAT = "DATE_FORMAT"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "collection_reproject"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Reproject raster collection"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Reproject every timestep of a stack of co-registered rasters to a target CRS. One "
            "file per timestep is written into the output directory, via pyramids."
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
        self.addParameter(QgsProcessingParameterCrs(self.CRS, "Target CRS"))
        self.addParameter(
            QgsProcessingParameterEnum(
                self.RESAMPLING, "Resampling method", options=RESAMPLING, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.MAINTAIN_ALIGNMENT, "Maintain source grid alignment", defaultValue=False
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
            QgsProcessingParameterFolderDestination(
                self.OUTPUT, "Reprojected collection (directory)"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids collection reproject`` command."""
        src = self.parameterAsFile(parameters, self.INPUT, context)
        validate_input_path(src, feedback)
        out = self.parameterAsString(parameters, self.OUTPUT, context)

        target_crs = crs_to_pyramids(self.parameterAsCrs(parameters, self.CRS, context))
        if target_crs is None:
            raise QgsProcessingException("A valid target CRS is required.")

        resampling = RESAMPLING[self.parameterAsEnum(parameters, self.RESAMPLING, context)]
        argv = ["collection", "reproject", src, out, "--crs", target_crs]
        argv += ["--resampling", resampling]

        if self.parameterAsBool(parameters, self.MAINTAIN_ALIGNMENT, context):
            argv.append("--maintain-alignment")
        date_format = self.parameterAsString(parameters, self.DATE_FORMAT, context).strip()
        if date_format:
            argv += ["--date-format", date_format]
        argv.append("--overwrite")

        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
