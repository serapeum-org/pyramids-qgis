"""Unit tests for the QGIS-free dependency probes in ``pyramids_qgis.dependencies``.

These functions are importable on a bare interpreter because ``dependencies.py`` imports PyQGIS
only inside the functions that raise, never at module load. The probes themselves use
``importlib.util.find_spec`` and the filesystem, both of which are monkeypatched here so the tests
are deterministic and need neither pyramids nor QGIS installed.
"""

from __future__ import annotations

import pytest
from qgis.core import QgsProcessingException

import pyramids_qgis.dependencies as deps


class _Spec:
    """Minimal stand-in for an ``importlib`` ModuleSpec with search locations."""

    def __init__(self, locations):
        """Store the submodule search locations the probe will inspect."""
        self.submodule_search_locations = locations


def test_pyramids_installed_reflects_find_spec(monkeypatch):
    """`pyramids_installed` is True exactly when `find_spec` locates the package."""
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())
    assert deps.pyramids_installed() is True
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
    assert deps.pyramids_installed() is False


def test_mesh_warning_present_only_when_absent(monkeypatch):
    """`mesh_drivers_warning` returns a hint iff pyramids-mesh cannot be located."""
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
    assert deps.mesh_drivers_warning() is not None
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())
    assert deps.mesh_drivers_warning() is None


def test_eo_installed_reflects_find_spec(monkeypatch):
    """`pyramids_eo_installed` is True exactly when `find_spec` locates the package."""
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())
    assert deps.pyramids_eo_installed() is True
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
    assert deps.pyramids_eo_installed() is False


def test_vendored_warning_detects_vendor_dir_on_disk(tmp_path, monkeypatch):
    """A `_vendor/osgeo` directory under the package location triggers the warning."""
    (tmp_path / "_vendor" / "osgeo").mkdir(parents=True)
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: _Spec([str(tmp_path)]))
    message = deps.vendored_gdal_warning()
    assert message is not None
    assert "vendors its own GDAL" in message


def test_vendored_warning_none_without_vendor_dir(tmp_path, monkeypatch):
    """A package location with no `_vendor/osgeo` yields no warning."""
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: _Spec([str(tmp_path)]))
    assert deps.vendored_gdal_warning() is None


def test_vendored_warning_none_when_pyramids_absent(monkeypatch):
    """When pyramids is not installed the warning is None (reported by ensure_pyramids instead).

    This is the regression the L2 fix closes: the old implementation imported osgeo and returned a
    'Could not import ...' string here, a false positive once QGIS's osgeo was cached.
    """
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
    assert deps.vendored_gdal_warning() is None


def test_vendored_warning_none_when_find_spec_raises(monkeypatch):
    """A broken/partial install whose `find_spec` raises yields no warning rather than erroring."""

    def boom(name):
        raise ValueError("partial pyramids install")

    monkeypatch.setattr(deps.importlib.util, "find_spec", boom)
    assert deps.vendored_gdal_warning() is None


def test_ensure_pyramids_raises_when_absent(monkeypatch):
    """`ensure_pyramids` raises with the install hint when pyramids cannot be located."""
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(QgsProcessingException, match="pyramids-core"):
        deps.ensure_pyramids()


def test_ensure_pyramids_silent_when_present(monkeypatch):
    """`ensure_pyramids` returns without raising when the package is locatable."""
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())
    assert deps.ensure_pyramids() is None


def test_ensure_pyramids_eo_raises_when_absent(monkeypatch):
    """`ensure_pyramids_eo` raises with its own hint when pyramids-eo is missing."""
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(QgsProcessingException, match="pyramids-eo"):
        deps.ensure_pyramids_eo()


def test_ensure_pyramids_eo_silent_when_present(monkeypatch):
    """`ensure_pyramids_eo` returns without raising when pyramids-eo is locatable."""
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())
    assert deps.ensure_pyramids_eo() is None
