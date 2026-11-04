"""End-to-end integration tests that run real algorithms on the bundled example dataset.

Unlike ``test_real_qgis.py`` (which only drives ``initAlgorithm`` / parameter construction),
these exercise the full ``processAlgorithm`` path: each test feeds the committed
``examples/data`` fixtures through ``QgsProcessingAlgorithm.run`` against real PyQGIS + pyramids
and asserts a valid output. This is the coverage gap #8 / #3 called out — a shipped fixture is
what makes real ``processAlgorithm`` runs possible. They run only where QGIS is available (the
pixi ``dev`` env / wheel-test job); the session-scoped ``qgis_app`` fixture in ``conftest.py``
brings up a headless ``QgsApplication`` first.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def _run(algorithm_cls, parameters: dict) -> dict:
    """Run an algorithm end-to-end and return its results, asserting it succeeded.

    Args:
        algorithm_cls: The ``PyramidsAlgorithm`` subclass to run.
        parameters: The parameter dict passed to ``QgsProcessingAlgorithm.run``.

    Returns:
        dict: The algorithm's results mapping.
    """
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback

    algorithm = algorithm_cls()
    algorithm.initAlgorithm({})
    results, ok = algorithm.run(parameters, QgsProcessingContext(), QgsProcessingFeedback())
    assert ok, f"{algorithm_cls.__name__} did not run successfully: {parameters}"
    return results


def _valid_raster(path: Path):
    """Load ``path`` as a raster layer and assert it is valid, returning the layer."""
    from qgis.core import QgsRasterLayer

    layer = QgsRasterLayer(str(path), path.stem)
    assert layer.isValid(), f"output is not a valid raster: {path}"
    return layer


def test_example_dem_loads_as_a_valid_raster(example_dem: Path) -> None:
    """The bundled DEM loads as a valid 32x32 EPSG:4326 raster."""
    layer = _valid_raster(example_dem)
    assert (layer.width(), layer.height()) == (32, 32)
    assert layer.crs().authid() == "EPSG:4326"


def test_example_aoi_loads_as_a_valid_vector(example_aoi: Path) -> None:
    """The bundled AOI loads as a valid single-feature EPSG:4326 polygon layer."""
    from qgis.core import QgsVectorLayer

    layer = QgsVectorLayer(str(example_aoi), "aoi", "ogr")
    assert layer.isValid()
    assert layer.featureCount() == 1
    assert layer.crs().authid() == "EPSG:4326"


def test_convert_round_trips_the_dem(example_dem: Path, tmp_path: Path) -> None:
    """`convert` re-saves the DEM in another format and yields a valid raster."""
    from pyramids_qgis.algorithms.conversion.convert import ConvertRaster

    out = tmp_path / "dem.img"
    _run(ConvertRaster, {"INPUT": str(example_dem), "DRIVER": "", "OUTPUT": str(out)})
    assert out.exists()
    _valid_raster(out)


def test_warp_reprojects_the_dem(example_dem: Path, tmp_path: Path) -> None:
    """`warp` reprojects the DEM to EPSG:3857 and the output carries the new CRS."""
    from pyramids_qgis.algorithms.raster.warp import WarpRaster

    out = tmp_path / "dem_3857.tif"
    _run(
        WarpRaster,
        {"INPUT": str(example_dem), "CRS": "EPSG:3857", "RESAMPLING": 0, "OUTPUT": str(out)},
    )
    layer = _valid_raster(out)
    assert layer.crs().authid() == "EPSG:3857"


def test_clip_by_mask_crops_the_dem(example_dem: Path, example_aoi: Path, tmp_path: Path) -> None:
    """`clip` with the AOI mask crops the DEM to a sub-window smaller than the full grid."""
    from pyramids_qgis.algorithms.raster.clip import ClipRaster

    out = tmp_path / "dem_clipped.tif"
    _run(ClipRaster, {"INPUT": str(example_dem), "MASK": str(example_aoi), "OUTPUT": str(out)})
    layer = _valid_raster(out)
    # The AOI covers only the centre of the raster, so the clip is strictly smaller than 32x32.
    assert layer.width() < 32
    assert layer.height() < 32


def test_rasterize_burns_the_aoi_onto_the_dem_grid(
    example_aoi: Path, example_dem: Path, tmp_path: Path
) -> None:
    """`rasterize` burns the AOI's ``value`` column onto the DEM's grid (via the template)."""
    from pyramids_qgis.algorithms.conversion.rasterize import Rasterize

    out = tmp_path / "aoi.tif"
    _run(
        Rasterize,
        {
            "INPUT": str(example_aoi),
            "TEMPLATE": str(example_dem),
            "COLUMN": "value",
            "OUTPUT": str(out),
        },
    )
    layer = _valid_raster(out)
    # The template is the DEM, so the output adopts its 32x32 grid.
    assert (layer.width(), layer.height()) == (32, 32)
    # The burn actually landed: a point inside the AOI polygon carries the column value 7.
    from qgis.core import QgsPointXY

    value, sampled = layer.dataProvider().sample(QgsPointXY(30.16, 30.15), 1)
    assert sampled, "could not sample the rasterized output at an interior point"
    assert value == 7, f"expected the burned value 7 inside the AOI, got {value}"
