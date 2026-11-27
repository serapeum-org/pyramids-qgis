"""Guards that no module reaches a QGIS enum value through its deprecated unscoped alias.

QGIS moved its enums under ``Qgis`` (``Qgis.ProcessingNumberParameterType.Double``) and kept the
old class-level spellings (``QgsProcessingParameterNumber.Double``) as deprecated aliases. On PyQt5
both resolve, so a reintroduced alias runs fine: ``initAlgorithm`` succeeds and every existing test
passes. Only the PyQt6 bindings QGIS 4 ships drop the aliases that carry no
``SIP_MONKEYPATCH_SCOPEENUM_UNNEST``, which is where the regression would finally surface.

Nothing else in the toolchain covers this. Ruff's ``F821`` catches a missing ``Qgis`` import, but no
selected rule knows an unscoped alias from a scoped one, and the runtime suite cannot tell them
apart on PyQt5. So the invariant is checked here, against the source text.

This module parses source with ``ast`` and never imports PyQGIS, keeping it runnable wherever the
sources are readable - the same reason ``test_packaging.py`` stays a layout check.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PACKAGE_DIR = _REPO_ROOT / "src" / "pyramids_qgis"

#: ``QgsProcessingParameterNumber.<member>`` -> ``Qgis.ProcessingNumberParameterType.<member>``.
_NUMBER_PARAMETER_TYPES = frozenset({"Integer", "Double"})

#: ``QgsProcessingParameterFile.<member>`` -> ``Qgis.ProcessingFileParameterBehavior.<member>``.
_FILE_PARAMETER_BEHAVIORS = frozenset({"File", "Folder"})

#: ``Qgis.<member>`` -> ``Qgis.MessageLevel.<member>``; the whole family, not just the one in use,
#: because the QGIS cookbook still shows ``Qgis.Critical`` and ``Qgis.Info`` for ``logMessage``.
_MESSAGE_LEVELS = frozenset({"Info", "Warning", "Critical", "Success", "NoLevel"})


def _scoped_replacement(owner: str, attribute: str) -> str | None:
    """Return the scoped spelling for a deprecated unscoped enum alias, else ``None``."""
    if owner == "QgsProcessingParameterNumber" and attribute in _NUMBER_PARAMETER_TYPES:
        return f"Qgis.ProcessingNumberParameterType.{attribute}"
    if owner == "QgsProcessingParameterFile" and attribute in _FILE_PARAMETER_BEHAVIORS:
        return f"Qgis.ProcessingFileParameterBehavior.{attribute}"
    if owner == "QgsProcessing" and attribute != "Type" and attribute.startswith("Type"):
        return f"Qgis.ProcessingSourceType.{attribute.removeprefix('Type')}"
    if owner == "Qgis" and attribute in _MESSAGE_LEVELS:
        return f"Qgis.MessageLevel.{attribute}"
    return None


def _unscoped_aliases(source: str, where: str) -> list[str]:
    """Return one complaint per deprecated unscoped enum alias read in ``source``."""
    found = []
    for node in ast.walk(ast.parse(source, filename=where)):
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
            continue
        replacement = _scoped_replacement(node.value.id, node.attr)
        if replacement is not None:
            found.append(f"{where}:{node.lineno}: {node.value.id}.{node.attr} -> {replacement}")
    return found


def _package_sources() -> list[Path]:
    """Return every Python module shipped inside the plugin package."""
    return sorted(_PACKAGE_DIR.rglob("*.py"))


def test_the_scan_covers_the_whole_plugin_package():
    """A mis-rooted glob would report a clean package by scanning nothing, so pin what it finds."""
    scanned = _package_sources()
    assert _PACKAGE_DIR / "plugin.py" in scanned, f"plugin.py missing from {len(scanned)} modules"
    assert len(scanned) > 50, f"the algorithm subpackages look unscanned, found {len(scanned)}"


def test_no_module_reads_a_deprecated_unscoped_qgis_enum_alias():
    """Every enum value in the package is reached through a scoped ``Qgis.<Enum>.<Member>``."""
    offences = [
        complaint
        for path in _package_sources()
        for complaint in _unscoped_aliases(
            path.read_text(encoding="utf-8"), str(path.relative_to(_REPO_ROOT).as_posix())
        )
    ]
    assert not offences, "deprecated unscoped QGIS enum aliases (break under PyQt6):\n" + "\n".join(
        offences
    )


@pytest.mark.parametrize(
    ("snippet", "expected"),
    [
        ("QgsProcessingParameterNumber.Integer", "Qgis.ProcessingNumberParameterType.Integer"),
        ("QgsProcessingParameterNumber.Double", "Qgis.ProcessingNumberParameterType.Double"),
        ("QgsProcessingParameterFile.File", "Qgis.ProcessingFileParameterBehavior.File"),
        ("QgsProcessingParameterFile.Folder", "Qgis.ProcessingFileParameterBehavior.Folder"),
        ("QgsProcessing.TypeRaster", "Qgis.ProcessingSourceType.Raster"),
        ("QgsProcessing.TypeVectorPolygon", "Qgis.ProcessingSourceType.VectorPolygon"),
        ("Qgis.Warning", "Qgis.MessageLevel.Warning"),
        ("Qgis.Critical", "Qgis.MessageLevel.Critical"),
    ],
)
def test_the_guard_flags_the_pre_refactor_spelling_of_each_enum_family(snippet, expected):
    """The scan really fires on each alias family, so a clean package is not a vacuous pass."""
    complaints = _unscoped_aliases(f"value = {snippet}\n", "probe.py")
    assert complaints == [f"probe.py:1: {snippet} -> {expected}"], (
        f"{snippet} should be reported as {expected}, got {complaints}"
    )


@pytest.mark.parametrize(
    "snippet",
    [
        "Qgis.ProcessingNumberParameterType.Double",
        "Qgis.ProcessingFileParameterBehavior.Folder",
        "Qgis.ProcessingSourceType.Raster",
        "Qgis.MessageLevel.Warning",
        "Qgis.MessageLevel",
        "QgsProcessingParameterNumber(self.INPUT, 'n')",
        "QgsProcessing.TEMPORARY_OUTPUT",
        "QgsProcessingParameterFile.__name__",
    ],
)
def test_the_guard_leaves_scoped_and_unrelated_attributes_alone(snippet):
    """Scoped enum reads, constructor calls and non-enum attributes must not be reported."""
    assert _unscoped_aliases(f"value = {snippet}\n", "probe.py") == [], (
        f"{snippet} is not a deprecated unscoped alias and must not be flagged"
    )
