"""Algorithm registry for the Pyramids Processing provider.

Each algorithm is a thin adapter over one ``pyramids`` CLI command. To add another command,
implement a :class:`~pyramids_qgis.algorithms.base.PyramidsAlgorithm` subclass and append it
to :data:`ALGORITHMS` — the provider picks it up with no further wiring.
"""

from __future__ import annotations

from .calc import RasterCalc
from .clip import ClipRaster
from .cog import CreateCog
from .convert import ConvertRaster
from .merge import MergeRasters
from .mesh_convert import MeshConvert
from .mesh_to_vector import MeshToVector
from .polygonize import Polygonize
from .rasterize import Rasterize
from .warp import WarpRaster

#: Every algorithm class the provider registers, grouped loosely by theme.
ALGORITHMS = [
    WarpRaster,
    ClipRaster,
    MergeRasters,
    RasterCalc,
    ConvertRaster,
    Rasterize,
    Polygonize,
    CreateCog,
    MeshConvert,
    MeshToVector,
]

__all__ = ["ALGORITHMS"]
