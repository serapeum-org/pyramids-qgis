"""Guards that every tool agrees the installed plugin folder is ``pyramids_qgis``.

The release tooling (qgis-plugin-ci), the manual deploy helper and the import package must all use
the same folder name. qgis-plugin-ci, when ``plugin_path`` is nested (``src/pyramids_qgis``), names
the packaged folder ``slugify(name, separator="_")`` rather than the path basename — so the plugin
``name`` in ``metadata.txt`` is what decides it. If that slug were ``pyramids`` it would shadow the
``pyramids`` library the plugin imports (`from pyramids import cli`), breaking every algorithm.
"""

from __future__ import annotations

import configparser
from pathlib import Path

from slugify import slugify

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PACKAGE_DIR = _REPO_ROOT / "src" / "pyramids_qgis"


def _plugin_name() -> str:
    """Return the ``name`` field from the QGIS plugin metadata."""
    parser = configparser.ConfigParser()
    parser.read(_PACKAGE_DIR / "metadata.txt", encoding="utf-8")
    return parser["general"]["name"]


def test_plugin_name_slugs_to_the_package_folder():
    """qgis-plugin-ci slugs a nested ``plugin_path`` to ``slugify(name, separator="_")``.

    That slug must equal the import package directory (`pyramids_qgis`); otherwise the released
    plugin installs under a different folder than the one developed and deployed.
    """
    assert slugify(_plugin_name(), separator="_") == _PACKAGE_DIR.name == "pyramids_qgis"


def test_plugin_folder_does_not_collide_with_the_pyramids_library():
    """The folder must not be ``pyramids`` — that would shadow the imported `pyramids` library."""
    assert slugify(_plugin_name(), separator="_") != "pyramids"


def test_deploy_target_matches_the_package_folder():
    """`deploy.py` installs the plugin under the same folder qgis-plugin-ci packages it as."""
    import deploy  # scripts/ is on the pytest pythonpath

    assert deploy.PLUGIN_NAME == _PACKAGE_DIR.name == "pyramids_qgis"
