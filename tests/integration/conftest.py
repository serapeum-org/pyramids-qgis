"""Fixtures for the end-to-end algorithm tests: tiny real raster and mesh inputs.

These build genuine on-disk inputs — a small GeoTIFF and a UGRID NetCDF — that the algorithms
read and process through real pyramids, so the end-to-end tests assert against actual outputs
rather than mocks. Both are generated once per session (cheaper and more portable than checking
binary fixtures into git, and immune to GDAL-version drift in a stored file).
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def tiny_raster(tmp_path_factory) -> Path:
    """An 8x6 single-band float32 GeoTIFF in EPSG:4326 with values in ``[0, 1]``.

    Small enough to process instantly. The ``[0, 1]`` range doubles as valid reflectance for the
    EO stretch algorithm, and the EPSG:4326 CRS gives the warp algorithm a real source CRS to
    reproject away from.
    """
    import numpy as np
    from osgeo import gdal, osr

    gdal.UseExceptions()
    path = tmp_path_factory.mktemp("raster") / "tiny.tif"
    cols, rows = 8, 6
    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(str(path), cols, rows, 1, gdal.GDT_Float32)
    dataset.SetGeoTransform([10.0, 0.01, 0.0, 50.0, 0.0, -0.01])
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    dataset.SetProjection(srs.ExportToWkt())
    values = np.linspace(0.0, 1.0, cols * rows, dtype="float32").reshape(rows, cols)
    dataset.GetRasterBand(1).WriteArray(values)
    dataset.FlushCache()
    dataset = None  # noqa: F841  (close the GDAL dataset by dropping the last reference)
    return path


@pytest.fixture(scope="session")
def ugrid_mesh(tmp_path_factory) -> Path:
    """A minimal two-face UGRID NetCDF mesh carrying one data variable.

    Built from a GeoDataFrame of two adjacent unit squares via ``UgridDataset.from_geodataframe``
    and written as UGRID NetCDF — the one mesh format pyramids-core reads and writes *without*
    pyramids-mesh, so the mesh end-to-end tests run in the conda dev env (which has no
    pyramids-mesh; it is not on conda-forge).
    """
    import geopandas as gpd
    from pyramids.netcdf.ugrid import UgridDataset
    from shapely.geometry import Polygon

    path = tmp_path_factory.mktemp("mesh") / "mesh.nc"
    polygons = [
        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
        Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
    ]
    gdf = gpd.GeoDataFrame({"depth": [1.5, 2.5]}, geometry=polygons, crs="EPSG:4326")
    UgridDataset.from_geodataframe(gdf).to_file(str(path))
    return path
