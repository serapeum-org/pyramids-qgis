"""Tests for the provider identity, the forced GeoJSON output extension, and the registry.

These import the full plugin under the conftest ``qgis`` stub, so they also prove the algorithm
registry resolves (every module imports cleanly and the classes instantiate) without QGIS.
"""

from __future__ import annotations

import pyramids_qgis.provider as provider_module
from pyramids_qgis.algorithms import ALGORITHMS
from pyramids_qgis.provider import PyramidsProvider


def test_provider_identity():
    """The provider exposes the stable id and display names used in algorithm ids."""
    provider = PyramidsProvider()
    assert provider.id() == "pyramids"
    assert provider.name() == "Pyramids"
    assert provider.longName() == "Pyramids GIS toolkit"


def test_vector_outputs_forced_to_geojson():
    """The provider pins vector output to GeoJSON so it matches the forced driver (M1)."""
    provider = PyramidsProvider()
    assert provider.supportedOutputVectorLayerExtensions() == ["geojson"]
    assert provider.defaultVectorFileExtension(True) == "geojson"
    assert provider.defaultVectorFileExtension(False) == "geojson"


def test_registry_names_are_unique():
    """Every registered algorithm has a distinct id (QGIS requires unique names per provider)."""
    names = [algorithm().name() for algorithm in ALGORITHMS]
    assert len(names) == len(set(names))
    assert len(names) == 13


def test_registry_group_ids():
    """The algorithms fall into exactly the four expected Processing groups."""
    group_ids = {algorithm().groupId() for algorithm in ALGORITHMS}
    assert group_ids == {"raster", "cog", "mesh", "eo"}


def test_loadalgorithms_registers_every_algorithm(monkeypatch):
    """loadAlgorithms adds one instance of each registered algorithm to the provider."""
    provider = PyramidsProvider()
    added = []
    monkeypatch.setattr(provider, "addAlgorithm", added.append, raising=False)
    provider.loadAlgorithms()
    assert len(added) == len(ALGORITHMS)


def test_icon_returns_an_icon_when_the_svg_is_present():
    """icon() loads the bundled SVG when it exists."""
    assert PyramidsProvider().icon() is not None


def test_icon_falls_back_when_the_svg_is_missing(monkeypatch, tmp_path):
    """icon() falls back to the base provider icon when the SVG is absent."""
    monkeypatch.setattr(provider_module, "_ICON", tmp_path / "missing.svg")
    assert PyramidsProvider().icon() is None
