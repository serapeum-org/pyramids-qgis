"""Guards that every tool agrees the installed plugin folder is ``pyramids_qgis``.

The release tooling (qgis-plugin-ci), the manual deploy helper and the import package must all use
the same folder name. qgis-plugin-ci, when ``plugin_path`` is nested (``src/pyramids_qgis``), names
the packaged folder ``slugify(name, separator="_")`` rather than the path basename — so the plugin
``name`` in ``metadata.txt`` is what decides it. If that slug were ``pyramids`` it would shadow the
``pyramids`` library the plugin imports (`from pyramids import cli`), breaking every algorithm.
"""

from __future__ import annotations

import configparser
import re
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


def test_no_config_reads_the_pre_src_source_metadata_path():
    """A source-tree read of `metadata.txt` in CI/release config must use `src/pyramids_qgis/`.

    Guards the H1 class of bug: the src move left `publish.yml` grepping the old
    `pyramids_qgis/metadata.txt`, which fails under `set -euo pipefail` and silently breaks the
    release job (it runs only after a release, so PR CI never sees it). Wheel/zip-inspection lines
    are skipped: inside the built wheel the package is correctly `pyramids_qgis/` (import layout,
    no `src/`), a different namespace from the source tree.
    """
    config_files = [
        *(_REPO_ROOT / ".github").rglob("*"),
        *(_REPO_ROOT / "scripts").rglob("*.py"),
        _REPO_ROOT / ".qgis-plugin-ci",
        _REPO_ROOT / ".pre-commit-config.yaml",
    ]
    offenders = []
    for path in config_files:
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for lineno, line in enumerate(lines, 1):
            if re.search(r"\.whl|zipfile|dist/", line):  # inspects the installed layout, not source
                continue
            for match in re.finditer(r"(?:src/)?pyramids_qgis/metadata\.txt", line):
                if not match.group().startswith("src/"):
                    offenders.append(f"{path.relative_to(_REPO_ROOT).as_posix()}:{lineno}")
    assert not offenders, f"stale (pre-src) source metadata.txt path in: {sorted(set(offenders))}"
