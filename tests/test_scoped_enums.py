"""Guards that no module reaches a QGIS enum value through a deprecated unscoped alias.

QGIS moved its enums under ``Qgis`` (``Qgis.ProcessingNumberParameterType.Double``) and kept the old
class-level spellings (``QgsProcessingParameterNumber.Double``) as deprecated aliases. **Both
spellings currently resolve on both bindings**, which is exactly why this check has to exist:

* on PyQt6, ``python/PyQt6/core/auto_additions/qgis.py`` defines each alias explicitly — e.g.
  ``QgsProcessingParameterNumber.Integer = Qgis.ProcessingNumberParameterType.Integer`` — and marks
  it ``is_monkey_patched``;
* on PyQt5, ``python/core/auto_additions/qgis.py`` needs no such line, because sip exposes an
  unscoped C++ enum's members at class scope natively.

So nothing in the runtime suite can tell a scoped read from an unscoped one: ``tests.yml`` was green
on ``main@7c6aa41``, which carried 97 unscoped aliases, on *both* the ``dev`` leg (qgis 4.2.3,
PyQt6) and the ``qt5`` leg (qgis 3.44.14, PyQt5). The aliases are deprecated, not broken, and the
day QGIS drops them is the day a reintroduced one stops working — long after review would catch it.
Hence a source-level check.

Detection is structural rather than a list of known enums: any ``QgsFoo.CapWordsAttribute`` (or
``Qgis.CapWordsAttribute``) that is not itself the base of a further attribute access is an unscoped
read, because the scoped form always has the enum type in between. That covers every alias family
reachable from the classes this package imports — not just the four it happens to use today — and
needs no vendored copy of QGIS's table. ``_SCOPED_FORMS`` only makes the message more specific for
the families in use; detection does not depend on it.

Known limitation: the nested spelling ``QgsProcessing.SourceType.TypeRaster`` is *not* flagged,
since ``QgsProcessing.SourceType`` is then the base of a further access and so looks scoped. It is
deprecated too; ``test_the_nested_type_level_spelling_is_a_known_blind_spot`` pins that gap so it is
recorded rather than mistaken for coverage.

This module parses source with ``ast`` and imports no PyQGIS, the same shape ``test_packaging.py``
takes of reading the source tree instead of importing it, so the check cannot be fooled by which
bindings happen to be installed. It is still not runnable without QGIS: ``conftest``'s session-wide
``qgis_app`` fixture is autouse and builds a real ``QgsApplication``, so a bare interpreter errors
every test in this file at ``conftest.py:56``. That also means this guard runs only in ``tests.yml``,
which supplies conda QGIS, and never in ``lint.yml``.

Scope against issue #58, which wires upstream's ``pyqgis4-checker`` into ``lint.yml``: that job is a
strict superset, reporting the checker's other rules too (``PyQt5`` imports, ``exec_``, ``QRegExp``,
``QDesktopWidget``, bare ``QVariant()``). It stays the broader gate. This file is deliberately the
narrow one: it needs no 3 GB container, and it covers the single rule all 97 renames in this change
depend on.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_PACKAGE_DIR = _REPO_ROOT / "src" / "pyramids_qgis"

#: The ten algorithm subpackages, so a mis-rooted scan cannot look clean by missing most of them.
_SUBPACKAGES = (
    "collection",
    "conversion",
    "eo",
    "fetch",
    "mesh",
    "nc",
    "process",
    "raster",
    "stac",
    "vector",
)

#: A QGIS class that owns enum aliases: ``Qgis`` itself, or any ``Qgs``-prefixed class.
_OWNER = re.compile(r"^(Qgis|Qgs[A-Z]\w*)$")

#: An enum member reads as CapWords. Excludes ``SCREAMING_SNAKE`` constants such as
#: ``QgsProcessing.TEMPORARY_OUTPUT``, dunders, and QGIS's camelCase methods.
_MEMBER = re.compile(r"^[A-Z][A-Za-z0-9]*$")

#: ``(owner, member)`` -> the exact scoped spelling, for the families this package uses. Only
#: sharpens the message; detection is structural and does not consult this table.
_SCOPED_FORMS = {
    ("QgsProcessingParameterNumber", "Integer"): "Qgis.ProcessingNumberParameterType.Integer",
    ("QgsProcessingParameterNumber", "Double"): "Qgis.ProcessingNumberParameterType.Double",
    ("QgsProcessingParameterFile", "File"): "Qgis.ProcessingFileParameterBehavior.File",
    ("QgsProcessingParameterFile", "Folder"): "Qgis.ProcessingFileParameterBehavior.Folder",
    ("Qgis", "Info"): "Qgis.MessageLevel.Info",
    ("Qgis", "Warning"): "Qgis.MessageLevel.Warning",
    ("Qgis", "Critical"): "Qgis.MessageLevel.Critical",
    ("Qgis", "Success"): "Qgis.MessageLevel.Success",
    ("Qgis", "NoLevel"): "Qgis.MessageLevel.NoLevel",
}


def _unscoped_aliases(source: str, where: str) -> list[str]:
    """Return one complaint per deprecated unscoped enum alias used in ``source``."""
    tree = ast.parse(source, filename=where)
    bases = {id(node.value) for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
            continue
        if not _OWNER.match(node.value.id) or not _MEMBER.match(node.attr):
            continue
        if id(node) in bases:
            # The enum type in a scoped read, e.g. ``Qgis.MessageLevel`` of
            # ``Qgis.MessageLevel.Warning``.
            continue
        scoped = _SCOPED_FORMS.get((node.value.id, node.attr), "Qgis.<Enum>." + node.attr)
        found.append(f"{where}:{node.lineno}: {node.value.id}.{node.attr} -> {scoped}")
    return found


def _package_sources() -> list[Path]:
    """Return every Python module shipped inside the plugin package."""
    return sorted(_PACKAGE_DIR.rglob("*.py"))


def test_the_scan_reaches_every_part_of_the_plugin_package():
    """A mis-rooted glob would look clean by scanning nothing, so pin what the scan reaches."""
    scanned = _package_sources()
    relative = {path.relative_to(_PACKAGE_DIR).as_posix() for path in scanned}
    assert "plugin.py" in relative, f"plugin.py missing from the {len(scanned)} modules scanned"
    missing = [
        name
        for name in _SUBPACKAGES
        if not any(r.startswith(f"algorithms/{name}/") for r in relative)
    ]
    assert not missing, f"no modules scanned for subpackage(s): {missing}"


def test_no_module_uses_a_deprecated_unscoped_qgis_enum_alias():
    """No module reads or assigns a QGIS enum through its deprecated class-level spelling."""
    offences = [
        complaint
        for path in _package_sources()
        for complaint in _unscoped_aliases(
            path.read_text(encoding="utf-8"), str(path.relative_to(_REPO_ROOT).as_posix())
        )
    ]
    assert not offences, (
        "deprecated unscoped QGIS enum aliases (they still resolve today, and stop working "
        "whenever QGIS drops the compatibility aliases):\n" + "\n".join(offences)
    )


@pytest.mark.parametrize(
    ("snippet", "expected"),
    [
        # the four families this package actually uses
        ("QgsProcessingParameterNumber.Integer", "Qgis.ProcessingNumberParameterType.Integer"),
        ("QgsProcessingParameterNumber.Double", "Qgis.ProcessingNumberParameterType.Double"),
        ("QgsProcessingParameterFile.File", "Qgis.ProcessingFileParameterBehavior.File"),
        ("QgsProcessingParameterFile.Folder", "Qgis.ProcessingFileParameterBehavior.Folder"),
        ("Qgis.Warning", "Qgis.MessageLevel.Warning"),
        ("Qgis.Critical", "Qgis.MessageLevel.Critical"),
        # families a hard-coded list missed: every one is reachable from a class this package
        # imports, and QgsProcessingParameterField is already constructed in conversion/rasterize.py
        ("QgsProcessing.TypeRaster", "Qgis.<Enum>.TypeRaster"),
        ("QgsProcessingParameterField.String", "Qgis.<Enum>.String"),
        ("QgsProcessingAlgorithm.FlagNoThreading", "Qgis.<Enum>.FlagNoThreading"),
        (
            "QgsProcessingProvider.FlagDeemphasiseSearchResults",
            "Qgis.<Enum>.FlagDeemphasiseSearchResults",
        ),
        ("QgsCoordinateReferenceSystem.PostgisCrsId", "Qgis.<Enum>.PostgisCrsId"),
        # the type-level alias, not just members of it
        ("QgsProcessingParameterNumber.Type", "Qgis.<Enum>.Type"),
    ],
)
def test_the_guard_flags_an_unscoped_alias(snippet, expected):
    """The scan really fires on each alias shape, so a clean package is not a vacuous pass."""
    assert _unscoped_aliases(f"value = {snippet}\n", "probe.py") == [
        f"probe.py:1: {snippet} -> {expected}"
    ], f"{snippet} should be reported as {expected}"


@pytest.mark.parametrize(
    "snippet",
    [
        "Qgis.ProcessingNumberParameterType.Double",
        "Qgis.ProcessingFileParameterBehavior.Folder",
        "Qgis.ProcessingSourceType.Raster",
        "Qgis.MessageLevel.Warning",
        "QgsProcessing.TEMPORARY_OUTPUT",
        "QgsProcessingParameterNumber(self.INPUT, 'n')",
        "QgsProcessingParameterFile.__name__",
        "QgsProcessingProvider.loadAlgorithms()",
    ],
)
def test_the_guard_leaves_scoped_and_unrelated_attributes_alone(snippet):
    """Scoped enum reads, constants, constructor calls and methods must not be reported."""
    assert _unscoped_aliases(f"value = {snippet}\n", "probe.py") == [], (
        f"{snippet} is not a deprecated unscoped alias and must not be flagged"
    )


def test_the_nested_type_level_spelling_is_a_known_blind_spot():
    """``QgsProcessing.SourceType.TypeRaster`` is deprecated but reads as scoped, so it slips."""
    assert _unscoped_aliases("value = QgsProcessing.SourceType.TypeRaster\n", "probe.py") == []
