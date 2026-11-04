"""Integration tests for the example-dataset generator (``examples/data/make_example_data.py``).

These guard the committed fixtures against drift: they regenerate the DEM and AOI with the generator
and assert its documented properties, plus that regeneration reproduces the committed bytes exactly.
Marked ``integration`` because the generator needs ``osgeo`` (GDAL/OGR), which is only present where
QGIS/GDAL is installed (the pixi ``dev`` env / wheel-test job).
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

GENERATOR = Path(__file__).resolve().parents[2] / "examples" / "data" / "make_example_data.py"


@pytest.fixture(scope="module")
def generator():
    """Load the standalone generator by path (``examples/data/`` is not on the import path)."""
    spec = importlib.util.spec_from_file_location("make_example_data", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    """Return the hex SHA-256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_make_dem_writes_a_32x32_epsg4326_int16_dem(generator, tmp_path):
    """make_dem writes a 32x32 Int16 EPSG:4326 raster with the gradient and NoData corner."""
    from osgeo import gdal

    out = tmp_path / "dem.tif"
    generator.make_dem(out)

    dataset = gdal.Open(str(out))
    assert (dataset.RasterXSize, dataset.RasterYSize) == (32, 32)
    band = dataset.GetRasterBand(1)
    assert band.DataType == gdal.GDT_Int16
    assert band.GetNoDataValue() == -9999
    assert "4326" in dataset.GetProjection()

    array = band.ReadAsArray()
    assert array[0, 0] == -9999  # the top-left NoData block
    assert array[5, 4] == 10 + 2 * 4 + 3 * 5  # gradient is 10 + 2*col + 3*row

    geotransform = dataset.GetGeoTransform()
    assert geotransform[0] == pytest.approx(30.0)
    assert geotransform[3] == pytest.approx(30.32)


def test_make_aoi_writes_a_single_epsg4326_polygon_with_value(generator, tmp_path):
    """make_aoi writes one EPSG:4326 polygon carrying value=7 over the DEM centre."""
    from osgeo import ogr

    out = tmp_path / "aoi.geojson"
    generator.make_aoi(out)

    dataset = ogr.Open(str(out))
    layer = dataset.GetLayer(0)
    assert layer.GetFeatureCount() == 1
    feature = layer.GetNextFeature()
    assert feature.GetField("value") == 7
    minx, maxx, miny, maxy = feature.GetGeometryRef().GetEnvelope()
    assert (minx, maxx, miny, maxy) == pytest.approx((30.08, 30.24, 30.08, 30.24))


def test_make_aoi_overwrites_an_existing_file(generator, tmp_path):
    """make_aoi replaces a pre-existing file (the unlink branch) instead of failing."""
    from osgeo import ogr

    out = tmp_path / "aoi.geojson"
    out.write_text("stale")
    generator.make_aoi(out)
    assert ogr.Open(str(out)).GetLayer(0).GetFeatureCount() == 1


def test_main_writes_both_fixtures_next_to_the_module(generator, tmp_path, monkeypatch, capsys):
    """main() writes both fixtures under HERE and prints what it wrote."""
    monkeypatch.setattr(generator, "HERE", tmp_path)
    generator.main()
    assert (tmp_path / "dem.tif").exists()
    assert (tmp_path / "aoi.geojson").exists()
    assert "wrote" in capsys.readouterr().out


def test_regeneration_is_byte_identical_to_the_committed_fixtures(generator, tmp_path):
    """Regenerating both fixtures reproduces the committed bytes exactly (no drift)."""
    committed = GENERATOR.parent
    generator.make_dem(tmp_path / "dem.tif")
    generator.make_aoi(tmp_path / "aoi.geojson")
    for name in ("dem.tif", "aoi.geojson"):
        regenerated, original = _sha256(tmp_path / name), _sha256(committed / name)
        assert regenerated == original, f"{name} drifted from the committed fixture"
