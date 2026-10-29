"""Convert a mesh file between formats via pyramids' ``UgridDataset`` + pyramids-mesh drivers.

Unlike the raster/vector algorithms, pyramids-mesh has no CLI, so this calls the pyramids
library directly: ``UgridDataset.read_file`` reads any supported mesh (UGRID NetCDF built in,
every other format — 2DM, Selafin, DFSU, XMDF, PLY, ... — through a pyramids-mesh driver), and
``UgridDataset.to_file`` writes UGRID NetCDF by default or a named driver format.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
)

from ...dependencies import mesh_drivers_warning
from ..base import PyramidsAlgorithm


class MeshConvert(PyramidsAlgorithm):
    """Read a mesh in any supported format and write it to another format."""

    GROUP = "Mesh"
    GROUP_ID = "mesh"

    INPUT = "INPUT"
    SOURCE_DRIVER = "SOURCE_DRIVER"
    TARGET_DRIVER = "TARGET_DRIVER"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "mesh_convert"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Convert mesh format"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Read a mesh file and write it in another format, through pyramids' UgridDataset. "
            "UGRID NetCDF is built in; other formats (2DM, Selafin, DFSU, XMDF, PLY, ...) need "
            "pyramids-mesh installed. Leave the target driver blank to write UGRID NetCDF; "
            "otherwise give a mesh driver name (not a GDAL driver). The source driver is "
            "normally detected — set it only to force a specific reader."
        )

    def initAlgorithm(self, config=None) -> None:  # noqa: N802
        """Declare the algorithm's parameters."""
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT, "Input mesh file", behavior=QgsProcessingParameterFile.File
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.SOURCE_DRIVER, "Source mesh driver (optional; default: detect)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.TARGET_DRIVER,
                "Target mesh driver (optional; blank = UGRID NetCDF)",
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT, "Output mesh file", fileFilter="NetCDF (*.nc);;All files (*.*)"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Read the input mesh and write it in the target format."""
        self.check_pyramids(feedback)
        hint = mesh_drivers_warning()
        if hint:
            feedback.pushInfo(hint)

        from pyramids.netcdf.ugrid import UgridDataset

        inp = self.parameterAsFile(parameters, self.INPUT, context)
        out = self.parameterAsFileOutput(parameters, self.OUTPUT, context)
        source_driver = (
            self.parameterAsString(parameters, self.SOURCE_DRIVER, context).strip() or None
        )
        target_driver = (
            self.parameterAsString(parameters, self.TARGET_DRIVER, context).strip() or None
        )

        # UgridDataset.to_file never infers the format from the suffix, so a non-NetCDF target
        # driver written to a .nc-named output makes content and extension disagree (review M1).
        if target_driver is not None and out.lower().endswith(".nc"):
            feedback.pushWarning(
                f"target driver {target_driver!r} does not write NetCDF, but the output name "
                f"ends in .nc ({out}); the file content and extension will disagree. Use an "
                "output name whose extension matches the driver's format."
            )

        feedback.pushInfo(
            f"reading {inp}"
            + (f" with driver {source_driver}" if source_driver else "")
            + f"; writing {out}"
            + (f" with driver {target_driver}" if target_driver else " as UGRID NetCDF")
        )
        try:
            mesh = UgridDataset.read_file(inp, driver=source_driver)
            mesh.to_file(out, driver=target_driver)
        except QgsProcessingException:
            raise
        except Exception as exc:  # noqa: BLE001  (report any library error cleanly)
            raise QgsProcessingException(f"mesh convert failed: {exc}") from exc

        return {self.OUTPUT: out}
