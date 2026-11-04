"""End-to-end tests: run one algorithm per group to a real output under real PyQGIS.

Where ``tests/integration/test_real_qgis.py`` stops at ``initAlgorithm`` (parameter construction),
these drive each algorithm's full ``run()`` against a genuine fixture and validate the output on
disk with GDAL/OGR — covering both ways an algorithm reaches pyramids:

- the CLI-backed path (``convert`` from the conversion group, ``warp`` from the raster group), and
- the library-direct path (``mesh_convert`` / ``mesh_to_vector``, and ``eo_stretch``).

This is the automated subset of the manual in-QGIS smoke test tracked in #3.
"""

from __future__ import annotations

import pytest
from qgis.core import QgsProcessingContext, QgsProcessingFeedback

from pyramids_qgis.algorithms.conversion.convert import ConvertRaster
from pyramids_qgis.algorithms.eo.stretch import EoStretch
from pyramids_qgis.algorithms.mesh.convert import MeshConvert
from pyramids_qgis.algorithms.mesh.to_vector import MeshToVector
from pyramids_qgis.algorithms.raster.warp import WarpRaster

pytestmark = pytest.mark.integration


def _run(algorithm, parameters):
    """``run`` the algorithm, returning ``(results, ok, feedback)``.

    Uses ``QgsProcessingAlgorithm.run``, which clones the algorithm and calls ``initAlgorithm`` on
    the clone internally, so the full prepare/process/post chain executes exactly as it would in the
    toolbox — with a plain context and feedback (no project or registry needed for file-in /
    file-out algorithms). The passed instance therefore needs no explicit ``initAlgorithm`` call.
    """
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()
    results, ok = algorithm.run(parameters, context, feedback)
    return results, ok, feedback


def _assert_raster(path, cols=None, data_type_name=None, bands=None):
    """Assert ``path`` is a readable raster, optionally checking size / dtype / band count.

    Returns the projection WKT so a caller can verify the CRS (e.g. via an authority code).
    """
    from osgeo import gdal

    gdal.UseExceptions()
    dataset = gdal.Open(str(path))
    assert dataset is not None, f"GDAL could not open {path}"
    try:
        band = dataset.GetRasterBand(1)
        assert band is not None
        if bands is not None:
            actual = dataset.RasterCount
            assert actual == bands, f"expected {bands} band(s), got {actual}"
        if cols is not None:
            assert dataset.RasterXSize == cols
        if data_type_name is not None:
            assert gdal.GetDataTypeName(band.DataType) == data_type_name
        projection = dataset.GetProjection() or ""
    finally:
        dataset = None  # noqa: F841  (release the GDAL handle)
    return projection


def test_warp_raster_end_to_end(tiny_raster, tmp_path):
    """``warp`` (raster group, CLI-backed) reprojects the fixture to EPSG:3857."""
    out = tmp_path / "warped.tif"
    results, ok, feedback = _run(
        WarpRaster(),
        {
            WarpRaster.INPUT: str(tiny_raster),
            WarpRaster.CRS: "EPSG:3857",
            WarpRaster.RESAMPLING: 0,  # nearest neighbor
            WarpRaster.OUTPUT: str(out),
        },
    )
    assert ok, feedback.textLog()
    assert results[WarpRaster.OUTPUT] == str(out)
    assert out.exists()
    projection = _assert_raster(out)

    from osgeo import osr

    srs = osr.SpatialReference(projection)
    assert srs.GetAuthorityCode(None) == "3857", projection


def test_convert_raster_end_to_end(tiny_raster, tmp_path):
    """``convert`` (conversion group, CLI-backed) re-encodes the fixture into a different driver.

    Writing to a ``.img`` output exercises the driver-from-extension inference that is the point of
    ``convert``: the GeoTIFF fixture comes back as an Erdas HFA raster, with its dtype, CRS, band
    count and pixel values preserved — so a byte-for-byte copy of the input would not satisfy it.
    """
    out = tmp_path / "converted.img"
    results, ok, feedback = _run(
        ConvertRaster(),
        {
            ConvertRaster.INPUT: str(tiny_raster),
            ConvertRaster.OUTPUT: str(out),
        },
    )
    assert ok, feedback.textLog()
    assert results[ConvertRaster.OUTPUT] == str(out)
    assert out.exists()

    from osgeo import gdal, osr

    gdal.UseExceptions()
    output = gdal.Open(str(out))
    source = gdal.Open(str(tiny_raster))
    try:
        assert output.GetDriver().ShortName == "HFA", output.GetDriver().ShortName
        assert output.RasterCount == 1
        assert output.RasterXSize == 8
        band = output.GetRasterBand(1)
        assert gdal.GetDataTypeName(band.DataType) == "Float32"
        assert osr.SpatialReference(output.GetProjection()).GetAuthorityCode(None) == "4326"
        assert band.ReadAsArray()[0, 0] == source.GetRasterBand(1).ReadAsArray()[0, 0]
    finally:
        output = None  # noqa: F841  (release the GDAL handle)
        source = None  # noqa: F841  (release the GDAL handle)


def test_mesh_convert_end_to_end(ugrid_mesh, tmp_path):
    """``mesh_convert`` (mesh group, library-direct) round-trips the UGRID NetCDF fixture."""
    out = tmp_path / "roundtrip.nc"
    results, ok, feedback = _run(
        MeshConvert(),
        {
            MeshConvert.INPUT: str(ugrid_mesh),
            MeshConvert.OUTPUT: str(out),
        },
    )
    assert ok, feedback.textLog()
    assert results[MeshConvert.OUTPUT] == str(out)
    assert out.exists() and out.stat().st_size > 0

    # The written file is a real UGRID NetCDF whose topology AND data survive the round-trip: two
    # faces and six nodes come back, and the 'depth' data variable still carries [1.5, 2.5].
    # Checking the data — not just the face count — rules out a passthrough copy that drops or
    # scrambles the data variables while leaving the mesh topology intact.
    from pyramids.netcdf.ugrid import UgridDataset

    mesh = UgridDataset.read_file(str(out))
    assert mesh.n_face == 2
    assert mesh.n_node == 6
    assert "depth" in mesh.data_variable_names
    depth = mesh.to_geodataframe(variable_name="depth", location="face")["depth"]
    assert sorted(round(float(value), 3) for value in depth) == [1.5, 2.5]


def test_mesh_to_vector_end_to_end(ugrid_mesh, tmp_path):
    """``mesh_to_vector`` (mesh group, library-direct) exports the two faces as GeoJSON polygons."""
    out = tmp_path / "faces.geojson"
    results, ok, feedback = _run(
        MeshToVector(),
        {
            MeshToVector.INPUT: str(ugrid_mesh),
            MeshToVector.LOCATION: 0,  # face
            MeshToVector.OUTPUT: str(out),
        },
    )
    assert ok, feedback.textLog()
    assert results[MeshToVector.OUTPUT] == str(out)
    assert out.exists()

    from osgeo import ogr

    ogr.UseExceptions()
    source = ogr.Open(str(out))
    assert source is not None, f"OGR could not open {out}"
    try:
        layer = source.GetLayer(0)
        assert layer.GetFeatureCount() == 2
    finally:
        source = None  # noqa: F841  (release the OGR handle)


def test_eo_stretch_end_to_end(tiny_raster, tmp_path):
    """``eo_stretch`` (EO group, library-direct via pyramids-eo) stretches to a uint8 raster."""
    out = tmp_path / "stretched.tif"
    results, ok, feedback = _run(
        EoStretch(),
        {
            EoStretch.INPUT: str(tiny_raster),
            EoStretch.KIND: 1,  # crude: fixed min/max rescale — deterministic on a tiny fixture
            EoStretch.DTYPE: "uint8",
            EoStretch.OUTPUT: str(out),
        },
    )
    assert ok, feedback.textLog()
    assert results[EoStretch.OUTPUT] == str(out)
    assert out.exists()
    _assert_raster(out, data_type_name="Byte", bands=1)

    # A real contrast stretch maps the input's [0, 1] range across most of [0, 255]; a no-op cast of
    # the float input to uint8 would instead floor every value into [0, 1]. Assert the output spread
    # so that degenerate cast — or an all-constant output — would fail.
    from osgeo import gdal

    gdal.UseExceptions()
    dataset = gdal.Open(str(out))
    try:
        minimum, maximum = dataset.GetRasterBand(1).ComputeRasterMinMax()
    finally:
        dataset = None  # noqa: F841  (release the GDAL handle)
    assert maximum >= 250, f"stretch did not reach the top of the uint8 range: max={maximum}"
    assert maximum - minimum >= 200, f"stretch span too narrow: [{minimum}, {maximum}]"
