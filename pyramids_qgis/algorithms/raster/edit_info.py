"""Assign a raster's CRS and/or NoData value — wraps ``pyramids convert`` + ``edit-info``.

This is the *assign projection* operation: it stamps the CRS / NoData metadata without
reprojecting or touching a single pixel — distinct from Reproject (warp), which resamples. A copy
is written to the output and the metadata is edited on that copy, so the input file is untouched.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterCrs,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
)

from ..base import PyramidsAlgorithm, crs_to_pyramids, layer_source_path, validate_input_path


class EditRasterInfo(PyramidsAlgorithm):
    """Assign a CRS and/or set the NoData value, writing a new raster (no reprojection)."""

    GROUP = "Raster"
    GROUP_ID = "raster"

    INPUT = "INPUT"
    CRS = "CRS"
    NODATA = "NODATA"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "edit_info"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Assign CRS / NoData (edit info)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Stamp a raster's CRS and/or NoData value without reprojecting or changing pixels — "
            "the 'assign projection' operation, distinct from Reproject (warp). Give a CRS to "
            "override the declared one, a NoData value, or both; a copy is written to the output "
            "and the original file is left untouched."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster"))
        self.addParameter(
            QgsProcessingParameterCrs(self.CRS, "CRS to assign (optional)", optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NODATA,
                "NoData value (optional)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
            )
        )
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT, "Output raster"))

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Copy the raster, then stamp the requested CRS / NoData onto the copy."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        crs = self.parameterAsCrs(parameters, self.CRS, context)
        crs_str = crs_to_pyramids(crs) if crs is not None and crs.isValid() else None
        has_nodata = self.NODATA in parameters and parameters[self.NODATA] is not None
        nodata = self.parameterAsDouble(parameters, self.NODATA, context) if has_nodata else None
        if crs_str is None and not has_nodata:
            raise QgsProcessingException("Provide a CRS to assign and/or a NoData value.")

        # Copy to the output first, then edit the copy in place — so the source stays untouched.
        self.run_pyramids(["convert", src, out, "--overwrite"], feedback)
        edit = ["edit-info", out]
        if crs_str is not None:
            edit += ["--crs", crs_str]
        if has_nodata:
            edit += ["--nodata", str(nodata)]
        self.run_pyramids(edit, feedback)

        return {self.OUTPUT: out}
