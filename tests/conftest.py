"""Test configuration: a headless QgsApplication for the real-PyQGIS test session.

The suite runs inside the pixi `dev` environment, which conda-installs `qgis`, so PyQGIS is always
present — there is no import stub (mesh-style: tests run against the real dependency). A single
session-scoped ``QgsApplication`` is created so the provider and algorithms can be instantiated and
their parameter definitions built against the QGIS runtime.

``QT_QPA_PLATFORM=offscreen`` is set at import time — before pytest collects the test modules, which
``import qgis.core`` at module load — so the Linux CI runner needs no display.

``QGIS_CUSTOM_CONFIG_PATH`` is deliberately **not** set. A ``QgsApplication`` built here is not the
QGIS desktop app, so ``QgsSettings`` writes to this process's own store rather than a user profile
(measured: ``%APPDATA%/python/.../python.ini``). The gui tests still save and restore the one key
they touch, so a developer running the suite locally sees no change to their QGIS configuration.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

#: The committed example dataset lives at the repo root under ``examples/data/`` so the docs /
#: algorithm help and the integration tests share one source of truth (never under ``tests/data/``).
EXAMPLE_DATA_DIR = Path(__file__).resolve().parents[1] / "examples" / "data"


@pytest.fixture(scope="session")
def example_data_dir() -> Path:
    """Return the ``examples/data/`` directory holding the bundled fixtures."""
    return EXAMPLE_DATA_DIR


@pytest.fixture(scope="session")
def example_dem(example_data_dir: Path) -> Path:
    """Return the path to the bundled 32x32 EPSG:4326 DEM GeoTIFF (``dem.tif``)."""
    path = example_data_dir / "dem.tif"
    assert path.exists(), f"example DEM is missing: {path}"
    return path


@pytest.fixture(scope="session")
def example_aoi(example_data_dir: Path) -> Path:
    """Return the path to the bundled EPSG:4326 AOI polygon (``aoi.geojson``)."""
    path = example_data_dir / "aoi.geojson"
    assert path.exists(), f"example AOI is missing: {path}"
    return path


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
