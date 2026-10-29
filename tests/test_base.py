"""Tests for the CLI runner and helpers in ``pyramids_qgis.algorithms.base``.

These run under the conftest ``qgis`` stub (which supplies the three ``qgis.core`` names base.py
imports). The pyramids CLI is replaced by a fake ``pyramids.cli`` module so the runner's exit-code
and error handling — including the L5 SystemExit shapes and the M2 capture-lock path — are exercised
without pyramids or QGIS installed.
"""

from __future__ import annotations

import sys
import threading
import types

import pytest
from qgis.core import QgsProcessingException

import pyramids_qgis.algorithms.base as base


class _Feedback:
    """Minimal QgsProcessingFeedback stand-in recording info/warning messages."""

    def __init__(self):
        """Start with empty message logs."""
        self.info: list[str] = []
        self.warnings: list[str] = []

    def pushInfo(self, message):  # noqa: N802 - mirrors the QGIS API name
        """Record an info message."""
        self.info.append(message)

    def pushWarning(self, message):  # noqa: N802 - mirrors the QGIS API name
        """Record a warning message."""
        self.warnings.append(message)


@pytest.fixture
def pyramids_present(monkeypatch):
    """Make the pyramids import guard pass and the vendored-GDAL warning stay silent."""
    monkeypatch.setattr(base, "ensure_pyramids", lambda: None)
    monkeypatch.setattr(base, "vendored_gdal_warning", lambda: None)


def _install_fake_cli(monkeypatch, main):
    """Register a fake ``pyramids.cli`` whose ``main`` is ``main``."""
    pyramids = types.ModuleType("pyramids")
    cli = types.ModuleType("pyramids.cli")
    cli.main = main
    pyramids.cli = cli
    monkeypatch.setitem(sys.modules, "pyramids", pyramids)
    monkeypatch.setitem(sys.modules, "pyramids.cli", cli)


def test_run_pyramids_success_logs_the_command(monkeypatch, pyramids_present):
    """A zero exit returns normally and the invoked command is logged."""
    _install_fake_cli(monkeypatch, lambda argv: 0)
    feedback = _Feedback()
    base.PyramidsAlgorithm().run_pyramids(["warp", "a", "b"], feedback)
    assert any("pyramids warp a b" in message for message in feedback.info)


def test_run_pyramids_nonzero_exit_raises_with_stderr(monkeypatch, pyramids_present):
    """A non-zero exit raises QgsProcessingException carrying the captured stderr."""

    def main(argv):
        print("error: bad crs", file=sys.stderr)
        return 1

    _install_fake_cli(monkeypatch, main)
    algorithm = base.PyramidsAlgorithm()
    feedback = _Feedback()
    with pytest.raises(QgsProcessingException, match="bad crs"):
        algorithm.run_pyramids(["warp"], feedback)


def test_run_pyramids_does_not_swallow_systemexit(monkeypatch, pyramids_present):
    """A SystemExit from the CLI propagates — it is never caught and converted (sonar S5754)."""

    def main(argv):
        raise SystemExit("stop")

    _install_fake_cli(monkeypatch, main)
    algorithm = base.PyramidsAlgorithm()
    feedback = _Feedback()
    with pytest.raises(SystemExit):
        algorithm.run_pyramids(["warp"], feedback)


def test_run_pyramids_propagates_missing_pyramids(monkeypatch):
    """A failing import guard propagates its QgsProcessingException unchanged."""

    def guard():
        raise QgsProcessingException("install pyramids-core")

    monkeypatch.setattr(base, "ensure_pyramids", guard)
    algorithm = base.PyramidsAlgorithm()
    feedback = _Feedback()
    with pytest.raises(QgsProcessingException, match="pyramids-core"):
        algorithm.run_pyramids(["warp"], feedback)


def test_run_pyramids_library_error_is_wrapped(monkeypatch, pyramids_present):
    """An unexpected library exception is wrapped as a clean QgsProcessingException."""

    def main(argv):
        raise RuntimeError("gdal blew up")

    _install_fake_cli(monkeypatch, main)
    algorithm = base.PyramidsAlgorithm()
    feedback = _Feedback()
    with pytest.raises(QgsProcessingException, match="gdal blew up"):
        algorithm.run_pyramids(["warp"], feedback)


def test_run_pyramids_passes_through_processing_exception(monkeypatch, pyramids_present):
    """A QgsProcessingException raised inside the call propagates unchanged (not re-wrapped)."""

    def main(argv):
        raise QgsProcessingException("passthrough")

    _install_fake_cli(monkeypatch, main)
    algorithm = base.PyramidsAlgorithm()
    feedback = _Feedback()
    with pytest.raises(QgsProcessingException, match="passthrough"):
        algorithm.run_pyramids(["warp"], feedback)


class _Crs:
    """Minimal QgsCoordinateReferenceSystem stand-in for crs_to_pyramids."""

    def __init__(self, valid, authid="", wkt=""):
        """Store validity and the authid/WKT the helper will read."""
        self._valid = valid
        self._authid = authid
        self._wkt = wkt

    def isValid(self):  # noqa: N802 - mirrors the QGIS API name
        """Return whether the CRS is valid."""
        return self._valid

    def authid(self):
        """Return the authority id, e.g. ``EPSG:3857``."""
        return self._authid

    def toWkt(self):  # noqa: N802 - mirrors the QGIS API name
        """Return the WKT representation."""
        return self._wkt


def test_crs_to_pyramids_prefers_epsg_authid():
    """A valid CRS with an EPSG authid returns that compact id."""
    assert base.crs_to_pyramids(_Crs(True, "EPSG:3857")) == "EPSG:3857"


def test_crs_to_pyramids_falls_back_to_wkt():
    """A valid CRS without an EPSG authid returns its WKT."""
    assert base.crs_to_pyramids(_Crs(True, "", "PROJCS[...]")) == "PROJCS[...]"


def test_crs_to_pyramids_invalid_is_none():
    """An invalid (or None) CRS returns None."""
    assert base.crs_to_pyramids(_Crs(False)) is None
    assert base.crs_to_pyramids(None) is None


def test_layer_source_path_strips_sublayer_suffix():
    """An OGR ``|layername=...`` suffix is dropped, leaving the file path."""

    class _Layer:
        def source(self):
            return "C:/x/data.gpkg|layername=roads"

    assert base.layer_source_path(_Layer()) == "C:/x/data.gpkg"


def test_validate_input_path_warns_for_missing_file(tmp_path):
    """A non-existent local source produces a warning (not an error)."""
    feedback = _Feedback()
    base.validate_input_path(str(tmp_path / "nope.tif"), feedback)
    assert feedback.warnings


def test_validate_input_path_quiet_for_existing_file(tmp_path):
    """An existing local source produces no warning."""
    path = tmp_path / "x.tif"
    path.write_text("x")
    feedback = _Feedback()
    base.validate_input_path(str(path), feedback)
    assert not feedback.warnings


def test_createinstance_returns_a_fresh_instance():
    """createInstance yields a new object of the same class (QGIS clones per run)."""
    algorithm = base.PyramidsAlgorithm()
    clone = algorithm.createInstance()
    assert isinstance(clone, base.PyramidsAlgorithm)
    assert clone is not algorithm


def test_group_groupid_and_tr():
    """group/groupId return the class constants and tr is an identity passthrough."""
    algorithm = base.PyramidsAlgorithm()
    assert algorithm.group() == base.PyramidsAlgorithm.GROUP_LABEL
    assert algorithm.groupId() == base.PyramidsAlgorithm.GROUP_ID
    assert algorithm.tr("hello") == "hello"


def test_check_pyramids_pushes_the_vendored_warning(monkeypatch):
    """check_pyramids forwards a non-empty vendored-GDAL warning to the feedback."""
    monkeypatch.setattr(base, "ensure_pyramids", lambda: None)
    monkeypatch.setattr(base, "vendored_gdal_warning", lambda: "vendored build!")
    feedback = _Feedback()
    base.PyramidsAlgorithm().check_pyramids(feedback)
    assert "vendored build!" in feedback.warnings


def test_run_pyramids_echoes_stdout_and_stderr(monkeypatch, pyramids_present):
    """On success, both captured stdout and stderr are echoed to the Processing log."""

    def main(argv):
        print("wrote out.tif")
        print("a note", file=sys.stderr)
        return 0

    _install_fake_cli(monkeypatch, main)
    feedback = _Feedback()
    base.PyramidsAlgorithm().run_pyramids(["warp"], feedback)
    assert any("wrote out.tif" in message for message in feedback.info)
    assert any("a note" in message for message in feedback.info)


def test_capture_lock_is_a_lock():
    """The CLI capture lock is a usable, non-reentrant lock."""
    assert hasattr(base._CLI_CAPTURE_LOCK, "acquire")
    assert base._CLI_CAPTURE_LOCK.acquire(blocking=False)
    base._CLI_CAPTURE_LOCK.release()
    assert isinstance(base._CLI_CAPTURE_LOCK, type(threading.Lock()))
