"""Integration tests for the example-dataset generator (``examples/data/make_example_data.py``).

These guard the committed fixtures against drift: they regenerate the DEM and AOI with the generator
and assert its documented properties, plus that regeneration reproduces the committed bytes exactly.
Marked ``integration`` because the generator needs ``osgeo`` (GDAL/OGR), which is only present where
QGIS/GDAL is installed (the pixi ``dev`` env / wheel-test job).
"""

from __future__ import annotations

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
    # Non-square (X-extent != Y-extent), so the (minX, maxX, minY, maxY) unpack order is checked.
    assert (minx, maxx, miny, maxy) == pytest.approx((30.06, 30.26, 30.09, 30.21))


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


def test_regeneration_reproduces_the_committed_fixtures(generator, tmp_path):
    """Regenerating reproduces the committed fixtures' content (array/georef/CRS, feature/geometry).

    Compares decoded content rather than raw bytes so the check is toolchain-independent: a GDAL /
    libtiff / zlib upgrade may re-encode the DEFLATE stream or change OGR's coordinate precision
    without changing what the fixtures mean, and that must not fail this test.
    """
    import numpy as np
    from osgeo import gdal, ogr, osr

    committed = GENERATOR.parent
    generator.make_dem(tmp_path / "dem.tif")
    generator.make_aoi(tmp_path / "aoi.geojson")

    fresh_dem = gdal.Open(str(tmp_path / "dem.tif"))
    committed_dem = gdal.Open(str(committed / "dem.tif"))
    assert np.array_equal(fresh_dem.ReadAsArray(), committed_dem.ReadAsArray()), "pixels drifted"
    assert fresh_dem.GetGeoTransform() == committed_dem.GetGeoTransform(), "geotransform drifted"
    fresh_nodata = fresh_dem.GetRasterBand(1).GetNoDataValue()
    committed_nodata = committed_dem.GetRasterBand(1).GetNoDataValue()
    assert fresh_nodata == committed_nodata, "NoData drifted"
    fresh_srs = osr.SpatialReference(fresh_dem.GetProjection())
    committed_srs = osr.SpatialReference(committed_dem.GetProjection())
    assert fresh_srs.IsSame(committed_srs), "CRS drifted"

    # Keep the DataSource refs alive — ogr.Open(...).GetLayer(0) alone lets the source be
    # garbage-collected, which invalidates the layer.
    fresh_ds = ogr.Open(str(tmp_path / "aoi.geojson"))
    committed_ds = ogr.Open(str(committed / "aoi.geojson"))
    fresh_aoi, committed_aoi = fresh_ds.GetLayer(0), committed_ds.GetLayer(0)
    assert fresh_aoi.GetFeatureCount() == committed_aoi.GetFeatureCount() == 1
    fresh_feature = fresh_aoi.GetNextFeature()
    committed_feature = committed_aoi.GetNextFeature()
    assert fresh_feature.GetField("value") == committed_feature.GetField("value"), "value drifted"
    fresh_geom = fresh_feature.GetGeometryRef()
    committed_geom = committed_feature.GetGeometryRef()
    assert fresh_geom.Equals(committed_geom), "geometry drifted"
