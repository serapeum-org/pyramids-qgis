"""Export a mesh's geometry to a vector layer via ``UgridDataset.to_geodataframe``.

Reads a mesh in any supported format (pyramids-mesh drivers), builds a GeoDataFrame of the
chosen mesh location — faces as polygons, nodes as points, edges as lines — optionally carrying
one data variable as an attribute, and writes it as GeoJSON that QGIS loads as a layer. This is
how a mesh in a format QGIS cannot open natively becomes visible on the map.
"""

from __future__ import annotations

from qgis.core import (
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
)

from ..dependencies import mesh_drivers_warning
from .base import PyramidsAlgorithm

#: Mesh locations, passed to ``to_geodataframe(location=...)``.
LOCATION = ["face", "node", "edge"]


class MeshToVector(PyramidsAlgorithm):
    """Convert a mesh to a vector layer (faces/nodes/edges), written as GeoJSON."""

    GROUP = "Mesh"
    GROUP_ID = "mesh"

    INPUT = "INPUT"
    SOURCE_DRIVER = "SOURCE_DRIVER"
    LOCATION = "LOCATION"
    VARIABLE = "VARIABLE"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        """Return the stable algorithm id within the provider."""
        return "mesh_to_vector"

    def displayName(self) -> str:  # noqa: N802
        """Return the human-readable algorithm name."""
        return "Mesh to vector"

    def shortHelpString(self) -> str:  # noqa: N802
        """Return the help shown in the algorithm dialog."""
        return (
            "Read a mesh file and export its geometry as a vector layer: faces as polygons, "
            "nodes as points, or edges as lines. Optionally include one data variable as an "
            "attribute column. UGRID NetCDF is built in; other formats need pyramids-mesh "
            "installed. The output is written as GeoJSON."
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
            QgsProcessingParameterEnum(
                self.LOCATION, "Mesh location", options=LOCATION, defaultValue=0
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.VARIABLE, "Data variable to include (optional)", optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT, "Vector output (GeoJSON)", defaultValue=None
            )
        )

    def processAlgorithm(self, parameters, context, feedback):  # noqa: N802
        """Read the mesh, build the GeoDataFrame, and write it as GeoJSON."""
        self.check_pyramids(feedback)
        hint = mesh_drivers_warning()
        if hint:
            feedback.pushInfo(hint)

        from pyramids.feature import FeatureCollection
        from pyramids.netcdf.ugrid import UgridDataset

        inp = self.parameterAsFile(parameters, self.INPUT, context)
        out = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)
        source_driver = (
            self.parameterAsString(parameters, self.SOURCE_DRIVER, context).strip() or None
        )
        location = LOCATION[self.parameterAsEnum(parameters, self.LOCATION, context)]
        variable = self.parameterAsString(parameters, self.VARIABLE, context).strip() or None

        feedback.pushInfo(f"reading {inp}; exporting {location} geometry to {out}")
        try:
            mesh = UgridDataset.read_file(inp, driver=source_driver)
            gdf = mesh.to_geodataframe(variable_name=variable, location=location)
            FeatureCollection(gdf).to_file(out, driver="geojson")
        except QgsProcessingException:
            raise
        except Exception as exc:  # noqa: BLE001  (report any library error cleanly)
            raise QgsProcessingException(f"mesh to vector failed: {exc}") from exc

        return {self.OUTPUT: out}
