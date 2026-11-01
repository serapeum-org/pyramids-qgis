"""Test configuration: a headless QgsApplication for the real-PyQGIS test session.

The suite runs inside the pixi `dev` environment, which conda-installs `qgis`, so PyQGIS is always
present — there is no import stub (mesh-style: tests run against the real dependency). A single
session-scoped ``QgsApplication`` is created so the provider and algorithms can be instantiated and
their parameter definitions built against the QGIS runtime.

``QT_QPA_PLATFORM=offscreen`` is set at import time — before pytest collects the test modules, which
``import qgis.core`` at module load — so the Linux CI runner needs no display.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session", autouse=True)
def qgis_app():
    """Bring up and tear down a headless QgsApplication once for the whole session."""
    from qgis.core import QgsApplication

    app = QgsApplication([], False)
    app.initQgis()
    try:
        yield app
    finally:
        app.exitQgis()
