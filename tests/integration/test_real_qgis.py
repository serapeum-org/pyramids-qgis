"""Integration tests that exercise the plugin against REAL PyQGIS.

These run only in an environment that actually provides QGIS (the pixi `dev` env, which
conda-installs `qgis`, or the wheel-test job) — they are marked ``integration`` and deselected by
the QGIS-free unit run (``pytest -m "not integration"``). They cover the one surface the import stub
cannot: instantiating the provider and the algorithms against the QGIS runtime and letting each
build its parameter definitions. The session-scoped ``qgis_app`` fixture in ``conftest.py`` brings
up a headless ``QgsApplication`` first.

Imports are deferred into the test bodies so that collecting this module under the stub (where it is
deselected anyway) never depends on anything beyond the stub.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def test_provider_registers_every_algorithm():
    """`loadAlgorithms` registers exactly the `ALGORITHMS` registry under real QGIS."""
    from pyramids_qgis.algorithms import ALGORITHMS
    from pyramids_qgis.provider import PyramidsProvider

    provider = PyramidsProvider()
    provider.loadAlgorithms()

    assert provider.id() == "pyramids"
    registered = {alg.name() for alg in provider.algorithms()}
    expected = {cls().name() for cls in ALGORITHMS}
    assert registered == expected
    assert len(provider.algorithms()) == len(ALGORITHMS)


@pytest.mark.parametrize(
    "index",
    range(13),
    ids=lambda i: f"alg{i}",
)
def test_each_algorithm_initialises_its_parameters(index):
    """Every algorithm instantiates and `initAlgorithm` builds its parameters against real PyQGIS.

    `initAlgorithm` is the PyQGIS-dependent path the unit-test stub cannot exercise — it constructs
    `QgsProcessingParameter*` objects, which need the QGIS runtime.
    """
    from pyramids_qgis.algorithms import ALGORITHMS

    if index >= len(ALGORITHMS):
        pytest.skip("fewer algorithms than the parametrised upper bound")
    alg = ALGORITHMS[index]()
    alg.initAlgorithm({})

    assert alg.name()
    assert alg.displayName()
    assert alg.group()
    # initAlgorithm must have declared at least one parameter for every algorithm.
    assert alg.parameterDefinitions()
