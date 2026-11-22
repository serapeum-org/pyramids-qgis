"""Tests for the plugin shell: the QGIS entry points, provider registration and teardown.

``classFactory`` (package level) and the ``initGui`` / ``initProcessing`` plugin methods are
implemented with snake_case names and surfaced under the QGIS-mandated camelCase names via
``__getattr__``. These tests prove the QGIS-facing API is intact, that unknown attributes still
raise ``AttributeError``, that each start hook registers the provider, and that only the GUI hook
schedules the ``pyramids-core`` install offer — headlessly there is no window to show it in.
"""

from __future__ import annotations

import pytest
from qgis.core import QgsApplication
from qgis.PyQt import QtCore

import pyramids_qgis
from pyramids_qgis.plugin import PyramidsPlugin
from pyramids_qgis.provider import PyramidsProvider


def _provider_is_registered() -> bool:
    """Report whether a provider with the ``pyramids`` id is in the Processing registry.

    Presence is checked by id rather than by Python-object identity: the registry owns the
    provider on the C++ side, so a wrapper fetched back out is not necessarily the same Python
    object.
    """
    return QgsApplication.processingRegistry().providerById("pyramids") is not None


@pytest.fixture
def clean_registry():
    """Assert the Processing registry starts free of a ``pyramids`` provider, and warn if one leaks.

    The registry is process-wide and the ``qgis_app`` fixture is session-scoped, so every test here
    unloads its own plugin while that plugin is still alive — the way QGIS does, since it holds the
    plugin in ``qgis.utils.plugins`` until ``unload``. This fixture only guards that invariant, so a
    future test that forgets to unload fails loudly instead of corrupting the ones after it.
    """
    assert not _provider_is_registered(), "a previous test leaked a registered pyramids provider"
    yield
    assert not _provider_is_registered(), "this test left a pyramids provider in the registry"


@pytest.fixture
def recording_timer(monkeypatch):
    """Replace ``QTimer`` with a stand-in recording ``singleShot`` calls instead of scheduling them.

    ``_init_gui`` imports ``QTimer`` from ``qgis.PyQt.QtCore`` when it runs, so replacing the
    attribute on that module is enough. It also keeps the deferred install offer from ever firing
    during the suite, which would try to open a modal dialog.
    """

    class RecordingTimer:
        """Stand-in for ``QTimer`` that records the deferred callbacks."""

        calls: list[tuple[int, object]] = []

        @classmethod
        def singleShot(cls, msec, callback):  # noqa: N802  (mirrors the Qt API name)
            """Record the scheduling request without running or queueing the callback."""
            cls.calls.append((msec, callback))

    RecordingTimer.calls = []
    monkeypatch.setattr(QtCore, "QTimer", RecordingTimer)
    return RecordingTimer


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


def test_init_stores_the_iface_and_defers_the_provider():
    """The constructor keeps the iface handle and creates no provider until a start hook runs."""
    iface = object()
    plugin = PyramidsPlugin(iface)
    assert plugin.iface is iface
    assert plugin.provider is None, "the provider must not be built before initGui/initProcessing"


def test_init_processing_registers_the_provider(clean_registry):
    """`init_processing` builds the provider and adds it to the Processing registry."""
    plugin = PyramidsPlugin(object())
    plugin.init_processing()
    try:
        assert isinstance(plugin.provider, PyramidsProvider)
        assert _provider_is_registered(), "init_processing did not register the provider"
    finally:
        plugin.unload()


def test_initprocessing_hook_registers_the_provider(clean_registry):
    """Called under the QGIS name, the headless hook registers the provider (the #44 path)."""
    plugin = PyramidsPlugin(object())
    plugin.initProcessing()
    try:
        assert _provider_is_registered(), "the initProcessing hook did not register the provider"
    finally:
        plugin.unload()


def test_initprocessing_does_not_schedule_the_install_offer(clean_registry, recording_timer):
    """The headless hook must not schedule the offer: there is no main window to show it in."""
    plugin = PyramidsPlugin(object())
    plugin.initProcessing()
    try:
        assert recording_timer.calls == [], f"headless start scheduled {recording_timer.calls}"
    finally:
        plugin.unload()


def test_init_gui_registers_the_provider_and_defers_the_offer(clean_registry, recording_timer):
    """The GUI hook registers the provider and defers the offer with a 0 ms timer (M1)."""
    plugin = PyramidsPlugin(object())
    plugin._init_gui()
    try:
        assert _provider_is_registered(), "_init_gui did not register the provider"
        assert len(recording_timer.calls) == 1, (
            f"expected one deferral, got {recording_timer.calls}"
        )
        msec, callback = recording_timer.calls[0]
        assert msec == 0, f"the offer must be deferred with a 0 ms timer, got {msec}"
        assert callback == plugin._offer_pyramids_install
    finally:
        plugin.unload()


def test_unload_removes_the_provider(clean_registry):
    """`unload` takes the provider out of the registry and clears the attribute."""
    plugin = PyramidsPlugin(object())
    plugin.init_processing()
    assert _provider_is_registered()
    plugin.unload()
    assert plugin.provider is None
    assert not _provider_is_registered(), "the provider outlived unload()"


def test_unload_without_a_provider_is_a_noop(clean_registry):
    """`unload` on a plugin that never started does nothing and does not raise."""
    plugin = PyramidsPlugin(object())
    plugin.unload()
    assert plugin.provider is None


def test_offer_pyramids_install_swallows_and_logs_failures(monkeypatch):
    """A failing offer is logged, never raised: plugin load must not fail because of it."""

    def boom():
        raise RuntimeError("offer exploded")

    plugin = PyramidsPlugin(object())
    monkeypatch.setattr(plugin, "_run_install_offer", boom)
    plugin._offer_pyramids_install()
