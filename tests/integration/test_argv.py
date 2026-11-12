"""Argv-capture tests: pin the exact ``pyramids`` argv each algorithm builds, under real PyQGIS.

These monkeypatch :meth:`PyramidsAlgorithm.run_pyramids` to record the argv list instead of
invoking pyramids, so they lock the CLI contract (flag names, the ``=``-join for negative-capable
numerics, the band base) without needing a real pyramids run or output data. They complement
``test_real_qgis`` (``initAlgorithm`` only) and ``test_end_to_end`` (full run to disk), and they
guard the Round 2 fixes: the ``--nodata=`` join (R2-M1), the 0-based render band (R2-M2), and the
empty-``--freq`` guard (R2-N1).
"""

from __future__ import annotations

import pytest
from qgis.core import QgsProcessingContext, QgsProcessingException, QgsProcessingFeedback

from pyramids_qgis.algorithms import base
from pyramids_qgis.algorithms.collection.merge import CollectionMerge
from pyramids_qgis.algorithms.collection.resample import CollectionResample
from pyramids_qgis.algorithms.raster.render import RasterRender

pytestmark = pytest.mark.integration

#: Canonical float32 fill — negative and in scientific notation, the shape that breaks a
#: two-token ``--nodata`` under argparse.
FLOAT32_FILL = -3.4e38


@pytest.fixture
def captured_argv(monkeypatch):
    """Record each argv passed to ``run_pyramids`` instead of invoking it; return the list."""
    calls: list[list[str]] = []

    def _capture(self, argv, feedback):  # noqa: ARG001
        calls.append(list(argv))
        return 0

    monkeypatch.setattr(base.PyramidsAlgorithm, "run_pyramids", _capture, raising=True)
    return calls


def _run(algorithm, parameters):
    """Run the algorithm through the full prepare/process chain with a plain context+feedback."""
    return algorithm.run(parameters, QgsProcessingContext(), QgsProcessingFeedback())


def test_merge_nodata_is_equals_joined(captured_argv, tiny_raster, tmp_path):
    """collection merge emits ``--nodata=<v>`` as one token, never a bare ``--nodata`` (R2-M1)."""
    _results, ok = _run(
        CollectionMerge(),
        {
            CollectionMerge.INPUT: str(tiny_raster),
            CollectionMerge.NODATA: FLOAT32_FILL,
            CollectionMerge.OUTPUT: str(tmp_path / "merged.tif"),
        },
    )
    assert ok
    argv = captured_argv[0]
    assert f"--nodata={FLOAT32_FILL}" in argv
    assert "--nodata" not in argv  # the two-token form that broke on a negative sci-notation value


def test_render_band_zero_is_reachable_and_emitted(captured_argv, tiny_raster, tmp_path):
    """render accepts band 0 and emits ``--band 0`` (band 0 was unreachable before — R2-M2)."""
    _results, ok = _run(
        RasterRender(),
        {
            RasterRender.INPUT: str(tiny_raster),
            RasterRender.BAND: 0,
            RasterRender.OUTPUT: str(tmp_path / "render.png"),
        },
    )
    assert ok  # fails as False under the old minValue=1, which rejects band 0
    argv = captured_argv[0]
    assert argv[argv.index("--band") + 1] == "0"


def test_resample_rejects_empty_freq(tiny_raster, tmp_path):
    """collection resample raises a clear QgsProcessingException on a blank ``--freq`` (R2-N1)."""
    algorithm = CollectionResample()
    algorithm.initAlgorithm(None)
    with pytest.raises(QgsProcessingException, match="frequency"):
        algorithm.processAlgorithm(
            {
                CollectionResample.INPUT: str(tiny_raster),
                CollectionResample.FREQ: "",
                CollectionResample.OP: 0,
                CollectionResample.OUTPUT: str(tmp_path / "out"),
            },
            QgsProcessingContext(),
            QgsProcessingFeedback(),
        )
