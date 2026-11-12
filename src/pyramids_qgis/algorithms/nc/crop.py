"""Crop a NetCDF cube to a bounding box — wraps ``pyramids nc crop``."""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
)

from ..base import PyramidsAlgorithm, validate_input_path


class NcCrop(PyramidsAlgorithm):
    """Crop a NetCDF cube to a rectangular window given in the file's own CRS."""

    GROUP_LABEL = "NetCDF"
    GROUP_ID = "nc"

    INPUT = "INPUT"
    EXTENT = "EXTENT"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "nc_crop"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Crop NetCDF (by bounding box)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Crop a NetCDF cube to a bounding box. The window is interpreted in the file's own "
            "CRS, so supply the extent in that CRS. A '.nc' output keeps the result a NetCDF, "
            "via pyramids."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(
            QgsProcessingParameterFile(self.INPUT, "Input NetCDF", extension="nc")
        )
        self.addParameter(
            QgsProcessingParameterExtent(self.EXTENT, "Crop window (in the file's CRS)")
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT, "Output NetCDF", fileFilter="NetCDF (*.nc)"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids nc crop`` command."""
        src = self.parameterAsFile(parameters, self.INPUT, context)
        validate_input_path(src, feedback)
        out = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        extent = self.parameterAsExtent(parameters, self.EXTENT, context)
        if extent.isNull():
            raise QgsProcessingException("A crop bounding box is required.")

        self.run_pyramids(
            [
                "nc",
                "crop",
                src,
                out,
                "--bbox",
                str(extent.xMinimum()),
                str(extent.yMinimum()),
                str(extent.xMaximum()),
                str(extent.yMaximum()),
                "--overwrite",
            ],
            feedback,
        )
        return {self.OUTPUT: out}
