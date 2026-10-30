"""Algorithm registry for the Pyramids Processing provider.

Algorithms are grouped into subpackages by origin and theme:

- ``raster`` — core raster processing (reproject, clip, merge, band calculator).
- ``conversion`` — format / representation conversion (convert, rasterize, polygonize, COG).
- ``mesh`` — pyramids-mesh-backed mesh algorithms.
- ``eo`` — pyramids-eo-backed Earth-observation algorithms.

Each algorithm is a thin adapter over the pyramids stack. To add one, implement a
:class:`~pyramids_qgis.algorithms.base.PyramidsAlgorithm` subclass in the right subpackage and
append it to :data:`ALGORITHMS` — the provider picks it up with no further wiring.
"""

from __future__ import annotations

from .conversion.cog import CreateCog
from .conversion.convert import ConvertRaster
from .conversion.polygonize import Polygonize
from .conversion.rasterize import Rasterize
from .eo.stretch import EoStretch
from .eo.tasseled_cap import TasseledCap
from .mesh.convert import MeshConvert
from .mesh.to_vector import MeshToVector
from .raster.calc import RasterCalc
from .raster.clip import ClipRaster
from .raster.edit_info import EditRasterInfo
from .raster.merge import MergeRasters
from .raster.warp import WarpRaster

#: Every algorithm class the provider registers, grouped by subpackage.
ALGORITHMS = [
    # raster
    WarpRaster,
    ClipRaster,
    MergeRasters,
    RasterCalc,
    EditRasterInfo,
    # conversion
    ConvertRaster,
    Rasterize,
    Polygonize,
    CreateCog,
    # mesh (pyramids-mesh)
    MeshConvert,
    MeshToVector,
    # eo (pyramids-eo)
    EoStretch,
    TasseledCap,
]

__all__ = ["ALGORITHMS"]
