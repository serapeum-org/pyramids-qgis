"""Guards that no module reaches a QGIS enum value through a deprecated unscoped alias.

QGIS moved its enums under ``Qgis`` (``Qgis.ProcessingNumberParameterType.Double``) and kept the old
class-level spellings (``QgsProcessingParameterNumber.Double``) as deprecated aliases. **Both
spellings currently resolve on both bindings**, which is exactly why this check has to exist:

* both bindings spell the ``Qgs*`` aliases out, and in identical numbers: release-3_40's
  ``python/PyQt6/core/auto_additions/qgis.py`` and ``python/core/auto_additions/qgis.py`` each
  carry 983 member aliases — e.g.
  ``QgsProcessingParameterNumber.Integer = Qgis.ProcessingNumberParameterType.Integer``, marked
  ``is_monkey_patched`` — plus 172 enum-*type* aliases such as ``QgsProcessing.SourceType``;
* only what hangs off ``Qgis`` itself differs: ``Qgis.Info`` … ``Qgis.NoLevel`` (PyQt6 file, lines
  72-76) and the 86 ``lambda flags=0:`` flag-type aliases are in the PyQt6 file and not the PyQt5
  one, because there sip exposes an unscoped C++ enum's members at class scope natively.

So nothing in the runtime suite can tell a scoped read from an unscoped one: ``tests.yml`` was green
on ``main@7c6aa41``, which carried 97 unscoped aliases, on *both* the ``dev`` leg (qgis 4.2.3,
PyQt6) and the ``qt5`` leg (qgis 3.44.14, PyQt5). The aliases are deprecated, not broken, and the
day QGIS drops them is the day a reintroduced one stops working — long after review would catch it.
Hence a source-level check.

Detection is structural rather than a list of known enums: any ``QgsFoo.CapWordsAttribute`` (or
``Qgis.CapWordsAttribute``) that is not itself the base of a further attribute access is an unscoped
read, because the scoped form always has the enum type in between. That covers every alias family
reachable from the classes this package imports — not just the four it happens to use today — and
needs no vendored copy of QGIS's table. ``_SCOPED_FORMS`` only makes the message more specific, and
for three of the four families in use at that; detection does not depend on it — emptying the table
and rescanning ``main@7c6aa41`` still reports all 97.

Being structural and purely lexical, the rule has three known gaps, each pinned by a test below so
it is recorded rather than mistaken for coverage:

* the nested spelling ``QgsProcessing.SourceType.TypeRaster`` slips, because the alias is then the
  base of a further access and so looks scoped
  (``test_the_nested_type_level_spelling_is_a_known_blind_spot``);
* an underscored alias such as ``QgsCoordinateReferenceSystem.WKT_PREFERRED`` slips, because
  ``_MEMBER`` excludes ``SCREAMING_SNAKE`` to leave genuine constants like
  ``QgsProcessing.TEMPORARY_OUTPUT`` and ``Qgis.QGIS_VERSION`` alone
  (``test_an_underscored_alias_is_a_known_blind_spot``);
* an alias reached other than through a literal ``Qgs``/``Qgis`` name — an aliased import, a
  variable, ``getattr``, a dotted ``qgis.core.Qgis`` owner — slips, and the dynamic forms are
  undecidable for any AST rule (``test_an_alias_reached_indirectly_is_a_known_blind_spot``).

It over-reports in one known shape, pinned the same way: a CapWords *nested class* or un-moved enum
*type* on a ``Qgs`` owner, e.g. ``QgsVectorLayer.LayerOptions()``, is not an alias at all but
matches the rule (``test_a_capwords_nested_class_is_a_known_over_report``). Narrowing either
direction would need a vendored copy of QGIS's alias table, which is what the structural rule exists
to avoid; issue #58's ``pyqgis4-checker`` is the gate that carries that table.

One narrowing looks free and is not: skipping an attribute that is *called*, on the reasoning that
an enum member is never invoked. It would silence ``QgsVectorLayer.LayerOptions()`` — but QGIS's
flag aliases are callable, e.g. ``Qgis.LoadStyleFlags = lambda flags=0: Qgis.LoadStyleFlag(flags)``
and ``QgsProcessingAlgorithm.Flags = Qgis.ProcessingAlgorithmFlags``, so it would also blind the
guard to ``QgsProcessingAlgorithm.Flags(...)`` — precisely the shape a ``flags()`` override uses.
Trading a recorded over-report for a silent miss is the wrong direction; do not make that change.

This module parses source with ``ast`` and imports no PyQGIS, the same shape ``test_packaging.py``
takes of reading the source tree instead of importing it, so the check cannot be fooled by which
bindings happen to be installed. It is still not runnable without QGIS: ``conftest``'s session-wide
``qgis_app`` fixture is autouse and builds a real ``QgsApplication``, so a bare interpreter errors
every test in this file at ``conftest.py:56``. That also means this guard runs only in
``tests.yml``, which supplies conda QGIS, and never in ``lint.yml``.

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

#: ``(owner, member)`` -> the exact scoped spelling, for three of the four families this package
#: uses — ``Qgis.ProcessingSourceType`` has no entry. Only sharpens the message; detection is
#: structural and does not consult this table.
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
    """Return one complaint per deprecated unscoped enum alias used in ``source``, in source order.

    ``ast.walk`` yields breadth-first, so the complaints are sorted back into ``(line, column)``
    order: the failure message is the whole point of this guard, and a 97-offence run that jumps
    about the file is far harder to work through than one that reads top to bottom.
    """
    tree = ast.parse(source, filename=where)
    bases = {id(node.value) for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    found: list[tuple[int, int, str]] = []
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
        complaint = f"{where}:{node.lineno}: {node.value.id}.{node.attr} -> {scoped}"
        found.append((node.lineno, node.col_offset, complaint))
    return [complaint for _, _, complaint in sorted(found)]


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
        # the three families ``_SCOPED_FORMS`` names, so the message carries the exact spelling
        ("QgsProcessingParameterNumber.Integer", "Qgis.ProcessingNumberParameterType.Integer"),
        ("QgsProcessingParameterNumber.Double", "Qgis.ProcessingNumberParameterType.Double"),
        ("QgsProcessingParameterFile.File", "Qgis.ProcessingFileParameterBehavior.File"),
        ("QgsProcessingParameterFile.Folder", "Qgis.ProcessingFileParameterBehavior.Folder"),
        ("Qgis.Warning", "Qgis.MessageLevel.Warning"),
        ("Qgis.Critical", "Qgis.MessageLevel.Critical"),
        # families a hard-coded list misses. ``QgsProcessing.TypeRaster`` is not hypothetical:
        # ``main@7c6aa41`` used it twice (raster/calc.py, raster/merge.py) and ``_SCOPED_FORMS``
        # still has no entry for it. The others are reachable from classes this package imports,
        # and QgsProcessingParameterField is already constructed in conversion/rasterize.py.
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


def test_complaints_are_reported_in_source_order():
    """``ast.walk`` is breadth-first, so pin that a deeply nested offence still sorts by line."""
    source = "def f():\n    if True:\n        x = Qgis.Warning\ny = Qgis.Critical\n"
    assert _unscoped_aliases(source, "probe.py") == [
        "probe.py:3: Qgis.Warning -> Qgis.MessageLevel.Warning",
        "probe.py:4: Qgis.Critical -> Qgis.MessageLevel.Critical",
    ], "a nested offence must not be reported after a later top-level one"


@pytest.mark.parametrize(
    "snippet",
    [
        # Every owner.member pair here is a real alias in QGIS's PyQt6 ``auto_additions/qgis.py``:
        # ``QgsProcessing.SourceType``, ``QgsProcessingParameterNumber.Type`` and
        # ``QgsMapLayer.LayerType`` each alias a ``Qgis`` enum type, so the read is deprecated.
        "QgsProcessing.SourceType.TypeRaster",
        "QgsProcessingParameterNumber.Type.Integer",
        "QgsMapLayer.LayerType.Vector",
    ],
)
def test_the_nested_type_level_spelling_is_a_known_blind_spot(snippet):
    """Reaching a member through the aliased enum *type* reads as scoped, so it slips through."""
    assert _unscoped_aliases(f"value = {snippet}\n", "probe.py") == [], (
        f"{snippet} is a recorded blind spot; if it now reports, delete this pin"
    )


@pytest.mark.parametrize(
    "snippet",
    [
        # ``QgsCoordinateReferenceSystem.WKT_PREFERRED = Qgis.CrsWktVariant.Preferred`` and its
        # ``WKT1_GDAL``/``WKT2_2019`` siblings are real aliases, and ``base.py`` already calls
        # ``crs.toWkt()`` one argument away from using one.
        "crs.toWkt(QgsCoordinateReferenceSystem.WKT_PREFERRED)",
        "QgsCoordinateReferenceSystem.WKT1_GDAL",
    ],
)
def test_an_underscored_alias_is_a_known_blind_spot(snippet):
    """``_MEMBER`` excludes ``SCREAMING_SNAKE``, so underscored aliases slip with the constants."""
    assert _unscoped_aliases(f"value = {snippet}\n", "probe.py") == [], (
        f"{snippet} is a recorded blind spot; if it now reports, delete this pin"
    )


@pytest.mark.parametrize(
    "source",
    [
        "from qgis.core import QgsProcessingParameterNumber as P\nvalue = P.Integer\n",
        "owner = QgsProcessingParameterNumber\nvalue = owner.Integer\n",
        "value = getattr(QgsProcessingParameterNumber, 'Integer')\n",
        "import qgis.core\nvalue = qgis.core.Qgis.Warning\n",
    ],
)
def test_an_alias_reached_indirectly_is_a_known_blind_spot(source):
    """The owner must be a literal ``Qgs``/``Qgis`` name, so indirection hides the alias."""
    assert _unscoped_aliases(source, "probe.py") == [], (
        "indirect alias reads are a recorded blind spot; if this now reports, delete this pin"
    )


@pytest.mark.parametrize(
    "snippet",
    [
        # None of these is an alias. The first three are nested classes (qgsvectorlayer.h:424,
        # qgsrasterlayer.h:113, qgsprocessingcontext.h:247); ``QgsTask.SubTaskDependency`` is an
        # unscoped enum QGIS never moved onto ``Qgis`` (qgstaskmanager.h:167 — only its *members*
        # are aliased). Every spelling shown is the correct, current one, so flagging them is the
        # price of needing no vendored table.
        "QgsVectorLayer.LayerOptions()",
        "QgsRasterLayer.LayerOptions()",
        "QgsProcessingContext.LayerDetails",
        "QgsTask.SubTaskDependency",
    ],
)
def test_a_capwords_nested_class_is_a_known_over_report(snippet):
    """A CapWords nested class or un-moved enum type matches the rule, so the guard over-reports."""
    assert len(_unscoped_aliases(f"value = {snippet}\n", "probe.py")) == 1, (
        f"{snippet} is a recorded over-report, not a real finding; if it is now silent, "
        "delete this pin"
    )
