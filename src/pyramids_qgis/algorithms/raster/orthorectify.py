"""Orthorectify a raster using its RPC model — wraps ``pyramids raster orthorectify``.

Removes sensor/terrain distortion from an RPC-tagged raster, optionally draping it over a DEM
(or a constant elevation when no DEM is given) and reprojecting the result.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterCrs,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
)

from ..base import PyramidsAlgorithm, crs_to_pyramids, layer_source_path, validate_input_path
from .warp import RESAMPLING


class RasterOrthorectify(PyramidsAlgorithm):
    """Orthorectify an RPC-tagged raster, optionally over a DEM and into a target CRS."""

    INPUT = "INPUT"
    DEM = "DEM"
    RPC_HEIGHT = "RPC_HEIGHT"
    TO_CRS = "TO_CRS"
    RESAMPLING = "RESAMPLING"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "raster_orthorectify"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Orthorectify (RPC)"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Orthorectify a raster that carries an RPC sensor model, via pyramids. Provide an "
            "elevation model (DEM) to drape over the terrain, or a constant RPC height to use "
            "when no DEM is given. Optionally reproject the orthorectified result to a target CRS."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT, "Input raster (RPC)"))
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.DEM, "Elevation model (DEM, optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.RPC_HEIGHT,
                "Constant RPC height (map units, used when no DEM)",
                type=QgsProcessingParameterNumber.Double,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                self.TO_CRS, "Reproject result to CRS (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.RESAMPLING, "Resampling method", options=RESAMPLING, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterDestination(self.OUTPUT, "Orthorectified raster")
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Build and run the ``pyramids raster orthorectify`` command."""
        layer = self.parameterAsRasterLayer(parameters, self.INPUT, context)
        if layer is None:
            raise QgsProcessingException(self.invalidRasterError(parameters, self.INPUT))
        src = layer_source_path(layer)
        validate_input_path(src, feedback)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        resampling = RESAMPLING[self.parameterAsEnum(parameters, self.RESAMPLING, context)]
        argv = ["raster", "orthorectify", src, out, "--resampling", resampling]

        dem_layer = self.parameterAsRasterLayer(parameters, self.DEM, context)
        if dem_layer is not None:
            dem_path = layer_source_path(dem_layer)
            validate_input_path(dem_path, feedback)
            argv += ["--dem", dem_path]

        if self.RPC_HEIGHT in parameters and parameters[self.RPC_HEIGHT] is not None:
            rpc_height = self.parameterAsDouble(parameters, self.RPC_HEIGHT, context)
            # '=' join: a negative elevation stringifies with a leading '-' that argparse would
            # otherwise read as an option rather than this flag's value (review R2-L4).
            argv.append(f"--rpc-height={rpc_height}")

        to_crs = self.parameterAsCrs(parameters, self.TO_CRS, context)
        to_crs_str = crs_to_pyramids(to_crs) if to_crs is not None and to_crs.isValid() else None
        if to_crs_str is not None:
            argv += ["--to-crs", to_crs_str]

        argv.append("--overwrite")
        self.run_pyramids(argv, feedback)
        return {self.OUTPUT: out}
