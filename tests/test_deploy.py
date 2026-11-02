"""Tests for the deploy helper's QGIS-profile path resolution (QGIS3 vs QGIS4)."""

from __future__ import annotations

import deploy  # scripts/ is on the pytest pythonpath
import pytest


def test_detect_prefers_qgis4_when_both_present(tmp_path):
    """Both generations installed → the newest (QGIS4) is chosen."""
    (tmp_path / "QGIS3").mkdir()
    (tmp_path / "QGIS4").mkdir()
    assert deploy._detect_qgis_dir(tmp_path) == "QGIS4"


def test_detect_falls_back_to_qgis3_when_only_qgis3(tmp_path):
    """Only a QGIS 3 tree present → deploy there, not into a non-existent QGIS4."""
    (tmp_path / "QGIS3").mkdir()
    assert deploy._detect_qgis_dir(tmp_path) == "QGIS3"


def test_detect_defaults_to_newest_when_none_present(tmp_path):
    """Fresh machine (no profile tree yet) → the newest known generation."""
    assert deploy._detect_qgis_dir(tmp_path) == "QGIS4"


def test_default_plugins_dir_autodetects_qgis4(tmp_path, monkeypatch):
    """Auto-detects the QGIS4 tree when present (regression: the path was hardcoded to QGIS3)."""
    (tmp_path / "QGIS4").mkdir()
    monkeypatch.setattr(deploy, "_qgis_config_base", lambda: tmp_path)
    result = deploy.default_plugins_dir("default")
    assert result == tmp_path / "QGIS4" / "profiles" / "default" / "python" / "plugins"


def test_default_plugins_dir_explicit_generation(tmp_path, monkeypatch):
    """An explicit qgis_dir overrides auto-detection."""
    (tmp_path / "QGIS4").mkdir()
    monkeypatch.setattr(deploy, "_qgis_config_base", lambda: tmp_path)
    result = deploy.default_plugins_dir("default", "QGIS3")
    assert result.parts[-5:] == ("QGIS3", "profiles", "default", "python", "plugins")


def test_default_plugins_dir_rejects_unknown_generation(tmp_path, monkeypatch):
    """A bogus generation is rejected rather than silently building a wrong path."""
    monkeypatch.setattr(deploy, "_qgis_config_base", lambda: tmp_path)
    with pytest.raises(ValueError, match="invalid QGIS generation"):
        deploy.default_plugins_dir("default", "QGIS9")


def test_default_plugins_dir_rejects_unsafe_profile():
    """Path-traversal profile names are still rejected (unchanged behaviour)."""
    with pytest.raises(ValueError, match="invalid QGIS profile name"):
        deploy.default_plugins_dir("../../etc")
