"""Tests that the QGIS entry points are exposed under their required names.

``classFactory`` (package level) and the ``initGui`` / ``initProcessing`` plugin methods are
implemented with snake_case names and surfaced under the QGIS-mandated camelCase names via
``__getattr__``. These tests prove the QGIS-facing API is intact and that unknown attributes still
raise ``AttributeError``.
"""

from __future__ import annotations

import pytest

import pyramids_qgis
from pyramids_qgis.plugin import PyramidsPlugin


def test_classfactory_is_exposed_and_builds_the_plugin():
    """`pyramids_qgis.classFactory(iface)` resolves and returns a PyramidsPlugin."""
    plugin = pyramids_qgis.classFactory(object())
    assert isinstance(plugin, PyramidsPlugin)


def test_unknown_package_attribute_raises():
    """A non-entry-point attribute on the package raises AttributeError."""
    with pytest.raises(AttributeError):
        _ = pyramids_qgis.does_not_exist


def test_initgui_is_exposed_under_the_qgis_name():
    """`plugin.initGui` resolves to the snake_case _init_gui and is callable."""
    plugin = PyramidsPlugin(object())
    assert plugin.initGui == plugin._init_gui
    assert callable(plugin.initGui)


def test_initprocessing_is_exposed_under_the_qgis_name():
    """`plugin.initProcessing` resolves to init_processing, which QGIS requires headlessly."""
    plugin = PyramidsPlugin(object())
    assert plugin.initProcessing == plugin.init_processing
    assert callable(plugin.initProcessing)


def test_both_start_hooks_exist_for_a_processing_provider_plugin():
    """Both lifecycle hooks exist: QGIS unloads the plugin if the one it starts with is missing."""
    plugin = PyramidsPlugin(object())
    assert hasattr(plugin, "initGui"), "the desktop GUI path calls initGui"
    assert hasattr(plugin, "initProcessing"), (
        "qgis.utils.startProcessingPlugin unloads a hasProcessingProvider plugin that has no "
        "initProcessing() method, making the algorithms unavailable to qgis_process"
    )


def test_unknown_instance_attribute_raises():
    """A non-existent instance attribute raises AttributeError."""
    plugin = PyramidsPlugin(object())
    with pytest.raises(AttributeError):
        _ = plugin.does_not_exist
