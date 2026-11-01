"""Integration tests that exercise the plugin against REAL PyQGIS.

These run only in an environment that actually provides QGIS (the pixi `dev` env, which
conda-installs `qgis`, or the wheel-test job). They instantiate the provider and every algorithm
against the QGIS runtime and let each build its parameter definitions. The session-scoped
``qgis_app`` fixture in ``conftest.py`` brings up a headless ``QgsApplication`` first.
"""

from __future__ import annotations

import pytest

from pyramids_qgis.algorithms import ALGORITHMS
from pyramids_qgis.provider import PyramidsProvider

pytestmark = pytest.mark.integration


def test_provider_registers_every_algorithm():
    """`loadAlgorithms` registers exactly the `ALGORITHMS` registry under real QGIS."""
    provider = PyramidsProvider()
    provider.loadAlgorithms()

    assert provider.id() == "pyramids"
    registered = {alg.name() for alg in provider.algorithms()}
    expected = {cls().name() for cls in ALGORITHMS}
    assert registered == expected
    assert len(provider.algorithms()) == len(ALGORITHMS)


@pytest.mark.parametrize("algorithm_cls", ALGORITHMS, ids=lambda cls: cls.__name__)
def test_each_algorithm_initialises_its_parameters(algorithm_cls):
    """Every algorithm instantiates and `initAlgorithm` builds its parameters against real PyQGIS.

    `initAlgorithm` is the PyQGIS-dependent path the unit tests cannot exercise — it constructs
    `QgsProcessingParameter*` objects, which need the QGIS runtime. Parametrising over `ALGORITHMS`
    (not a fixed count) means a newly added algorithm is covered automatically.
    """
    alg = algorithm_cls()
    alg.initAlgorithm({})

    assert alg.name()
    assert alg.displayName()
    assert alg.group()
    # initAlgorithm must have declared at least one parameter for every algorithm.
    assert alg.parameterDefinitions()
