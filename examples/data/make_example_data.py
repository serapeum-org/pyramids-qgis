"""Regenerate the bundled example dataset (``dem.tif`` + ``aoi.geojson``).

These tiny fixtures are committed to the repo so the docs/algorithm help and the integration
tests (``tests/integration/test_example_dataset.py``) share one source of truth. Run this only
to recreate them; it needs GDAL/OGR (the pixi ``dev`` environment, which conda-installs ``qgis``
and so provides ``osgeo``). It is deterministic — rerunning it produces byte-identical files.

    pixi run -e dev python examples/data/make_example_data.py

- ``dem.tif`` — a 32x32 Int16 "elevation" raster in EPSG:4326 over a small AOI near 30degN /
  30degE, with a left-to-right / top-to-bottom gradient, 0.01deg pixels, and ``-9999`` NoData in
  the top-left corner (so NoData handling is exercised).
- ``aoi.geojson`` — one polygon in EPSG:4326 covering the centre of the raster, carrying an
  integer ``value`` attribute (used by the rasterize example to burn a column).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from osgeo import gdal, ogr, osr

gdal.UseExceptions()

HERE = Path(__file__).resolve().parent

# DEM grid: 32x32, 0.01deg pixels, north-up, top-left at lon=30.0 / lat=30.32 (so the raster spans
# lon [30.00, 30.32] and lat [30.00, 30.32]).
NX = NY = 32
PIXEL = 0.01
ORIGIN_X = 30.0
ORIGIN_Y = 30.32
NODATA = -9999


def make_dem(path: Path) -> None:
    """Write the 32x32 Int16 EPSG:4326 DEM with a gradient and a NoData corner."""
    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(str(path), NX, NY, 1, gdal.GDT_Int16, options=["COMPRESS=DEFLATE"])
    dataset.SetGeoTransform([ORIGIN_X, PIXEL, 0.0, ORIGIN_Y, 0.0, -PIXEL])
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    dataset.SetProjection(srs.ExportToWkt())

    rows, cols = np.mgrid[0:NY, 0:NX]
    elevation = (10 + cols * 2 + rows * 3).astype("int16")
    elevation[0:3, 0:3] = NODATA  # a NoData block in the top-left corner

    band = dataset.GetRasterBand(1)
    band.SetNoDataValue(NODATA)
    band.WriteArray(elevation)
    band.FlushCache()
    dataset = None


def make_aoi(path: Path) -> None:
    """Write a single-polygon EPSG:4326 GeoJSON over the DEM centre, with a ``value`` attribute."""
    if path.exists():
        path.unlink()  # OGR GeoJSON will not overwrite an existing file
    driver = ogr.GetDriverByName("GeoJSON")
    source = driver.CreateDataSource(str(path))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    layer = source.CreateLayer("aoi", srs, ogr.wkbPolygon)
    layer.CreateField(ogr.FieldDefn("value", ogr.OFTInteger))

    ring = ogr.Geometry(ogr.wkbLinearRing)
    for lon, lat in [
        (30.08, 30.08),
        (30.24, 30.08),
        (30.24, 30.24),
        (30.08, 30.24),
        (30.08, 30.08),
    ]:
        ring.AddPoint_2D(lon, lat)  # 2D so the GeoJSON carries no spurious z=0 coordinate
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(ring)

    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetField("value", 7)
    feature.SetGeometry(polygon)
    layer.CreateFeature(feature)
    feature = None
    source = None


def main() -> None:
    """Regenerate both fixtures next to this script."""
    make_dem(HERE / "dem.tif")
    make_aoi(HERE / "aoi.geojson")
    print(f"wrote {HERE / 'dem.tif'} and {HERE / 'aoi.geojson'}")


if __name__ == "__main__":
    main()
