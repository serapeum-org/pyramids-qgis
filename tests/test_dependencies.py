"""Unit tests for the QGIS-free dependency probes in ``pyramids_qgis.dependencies``.

These functions are importable on a bare interpreter because ``dependencies.py`` imports PyQGIS
only inside the functions that raise, never at module load. The probes themselves use
``importlib.util.find_spec`` and the filesystem, both of which are monkeypatched here so the tests
are deterministic and need neither pyramids nor QGIS installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import pyramids_qgis.dependencies as deps


class _Spec:
    """Minimal stand-in for an ``importlib`` ModuleSpec with search locations."""

    def __init__(self, locations):
        """Store the submodule search locations the probe will inspect."""
        self.submodule_search_locations = locations


def test_pyramids_installed_reflects_find_spec(monkeypatch):
    """`pyramids_installed` is True exactly when `find_spec` locates the package."""
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())
    assert deps.pyramids_installed() is True
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
    assert deps.pyramids_installed() is False


def test_installed_probes_false_when_find_spec_raises(monkeypatch):
    """A broken install (find_spec raises) makes every *_installed probe return False, not raise."""

    def boom(name):
        raise ValueError("partial pyramids install")

    monkeypatch.setattr(deps.importlib.util, "find_spec", boom)
    assert deps.pyramids_installed() is False
    assert deps.pyramids_eo_installed() is False
    assert deps.pyramids_mesh_installed() is False


def test_mesh_warning_present_only_when_absent(monkeypatch):
    """`mesh_drivers_warning` returns a hint iff pyramids-mesh cannot be located."""
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
    assert deps.mesh_drivers_warning() is not None
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())
    assert deps.mesh_drivers_warning() is None


def test_eo_installed_reflects_find_spec(monkeypatch):
    """`pyramids_eo_installed` is True exactly when `find_spec` locates the package."""
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())
    assert deps.pyramids_eo_installed() is True
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
    assert deps.pyramids_eo_installed() is False


def test_vendored_warning_detects_vendor_dir_on_disk(tmp_path, monkeypatch):
    """A `_vendor/osgeo` directory under the package location triggers the warning."""
    (tmp_path / "_vendor" / "osgeo").mkdir(parents=True)
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: _Spec([str(tmp_path)]))
    message = deps.vendored_gdal_warning()
    assert message is not None
    assert "vendors its own GDAL" in message


def test_vendored_warning_none_without_vendor_dir(tmp_path, monkeypatch):
    """A package location with no `_vendor/osgeo` yields no warning."""
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: _Spec([str(tmp_path)]))
    assert deps.vendored_gdal_warning() is None


def test_vendored_warning_none_when_pyramids_absent(monkeypatch):
    """When pyramids is not installed the warning is None (reported by ensure_pyramids instead).

    This is the regression the L2 fix closes: the old implementation imported osgeo and returned a
    'Could not import ...' string here, a false positive once QGIS's osgeo was cached.
    """
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
    assert deps.vendored_gdal_warning() is None


def test_vendored_warning_none_when_find_spec_raises(monkeypatch):
    """A broken/partial install whose `find_spec` raises yields no warning rather than erroring."""

    def boom(name):
        raise ValueError("partial pyramids install")

    monkeypatch.setattr(deps.importlib.util, "find_spec", boom)
    assert deps.vendored_gdal_warning() is None


def test_ensure_pyramids_raises_when_absent(monkeypatch):
    """`ensure_pyramids` raises the install hint when pyramids cannot be located (needs QGIS)."""
    qgis_core = pytest.importorskip("qgis.core")
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(qgis_core.QgsProcessingException, match="pyramids-core"):
        deps.ensure_pyramids()


def test_ensure_pyramids_silent_when_present(monkeypatch):
    """`ensure_pyramids` returns without raising when the package is locatable (needs QGIS)."""
    pytest.importorskip("qgis.core")
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())
    assert deps.ensure_pyramids() is None


def test_ensure_pyramids_eo_raises_when_absent(monkeypatch):
    """`ensure_pyramids_eo` raises its own hint when pyramids-eo is missing (needs QGIS)."""
    qgis_core = pytest.importorskip("qgis.core")
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(qgis_core.QgsProcessingException, match="pyramids-eo"):
        deps.ensure_pyramids_eo()


def test_ensure_pyramids_eo_silent_when_present(monkeypatch):
    """`ensure_pyramids_eo` returns without raising when pyramids-eo is locatable (needs QGIS)."""
    pytest.importorskip("qgis.core")
    monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: object())
    assert deps.ensure_pyramids_eo() is None


class TestVersionTuple:
    """Tests for the ``_version_tuple`` parser."""

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("1.2.3", (1, 2, 3)),
            ("0.81.0", (0, 81, 0)),
            ("0.81", (0, 81)),
            ("0.81.0rc1", (0, 81, 0)),
            ("1.2.dev0", (1, 2)),
            ("2", (2,)),
            ("", ()),
            ("abc", ()),
            ("1.x.3", (1,)),
        ],
    )
    def test_parses_leading_integers(self, text, expected):
        """Keep the leading dotted integers and stop at the first non-digit chunk.

        Args:
            text: A version string.
            expected: The expected integer tuple.

        Test scenario:
            Covers full x.y.z, pre-release/dev suffixes, a bare major, empty, and non-numeric.
        """
        result = deps._version_tuple(text)
        assert result == expected, f"{text!r} -> {result}, expected {expected}"


class TestPyramidsVersion:
    """Tests for ``pyramids_version`` across the two distribution names."""

    def test_reads_first_distribution(self, monkeypatch):
        """Return the parsed version from the primary ('pyramids-core') distribution."""
        monkeypatch.setattr(deps.importlib.metadata, "version", lambda name: "0.81.0")
        assert deps.pyramids_version() == (0, 81, 0), "should parse the pyramids-core version"

    def test_falls_back_to_conda_name(self, monkeypatch):
        """Fall back to the conda 'pyramids' distribution when 'pyramids-core' is absent."""

        def fake(name):
            if name == "pyramids-core":
                raise deps.importlib.metadata.PackageNotFoundError(name)
            return "0.79.2"

        monkeypatch.setattr(deps.importlib.metadata, "version", fake)
        assert deps.pyramids_version() == (0, 79, 2), "should read the conda distribution name"

    def test_none_when_neither_found(self, monkeypatch):
        """Return None when neither distribution name resolves."""

        def fake(name):
            raise deps.importlib.metadata.PackageNotFoundError(name)

        monkeypatch.setattr(deps.importlib.metadata, "version", fake)
        assert deps.pyramids_version() is None, "unknown version should be None"

    def test_unparseable_version_is_none(self, monkeypatch):
        """A version string with no leading digits (e.g. 'unknown') is reported as None (N2)."""
        monkeypatch.setattr(deps.importlib.metadata, "version", lambda name: "unknown")
        assert deps.pyramids_version() is None, "a no-digit version string should map to None"


class TestPyramidsOutdated:
    """Tests for ``pyramids_outdated`` against the version floor."""

    @pytest.mark.parametrize(
        "version, outdated",
        [
            ((0, 2, 0), True),
            ((0, 80, 999), True),
            ((0, 81), False),
            ((0, 81, 0), False),
            ((0, 81, 0, 1), False),
            ((0, 82, 0), False),
            ((1, 0, 0), False),
            (None, False),
        ],
    )
    def test_outdated_against_floor(self, monkeypatch, version, outdated):
        """Only a known version below :data:`MIN_PYRAMIDS_VERSION` counts as outdated.

        Args:
            version: The value ``pyramids_version`` is stubbed to return.
            outdated: Whether that version should be reported as outdated.
        """
        monkeypatch.setattr(deps, "pyramids_version", lambda: version)
        assert deps.pyramids_outdated() is outdated, f"version {version} -> {not outdated}"


class TestVendorsGdal:
    """Tests for the ``_vendors_gdal`` filesystem probe."""

    def test_true_when_vendor_dir_present(self, tmp_path, monkeypatch):
        """A ``_vendor/osgeo`` directory under the package location is detected."""
        (tmp_path / "_vendor" / "osgeo").mkdir(parents=True)
        monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: _Spec([str(tmp_path)]))
        assert deps._vendors_gdal() is True, "vendor dir should be detected"

    def test_false_without_vendor_dir(self, tmp_path, monkeypatch):
        """A package location with no ``_vendor/osgeo`` is not flagged."""
        monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: _Spec([str(tmp_path)]))
        assert deps._vendors_gdal() is False, "no vendor dir -> False"

    def test_false_when_absent(self, monkeypatch):
        """A missing package (find_spec None) is not flagged."""
        monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: None)
        assert deps._vendors_gdal() is False, "absent package -> False"

    def test_false_when_no_search_locations(self, monkeypatch):
        """A spec without submodule search locations is not flagged."""
        monkeypatch.setattr(deps.importlib.util, "find_spec", lambda name: _Spec(None))
        assert deps._vendors_gdal() is False, "no search locations -> False"

    def test_false_when_find_spec_raises(self, monkeypatch):
        """A broken install whose find_spec raises is swallowed to False."""

        def boom(name):
            raise ValueError("partial pyramids install")

        monkeypatch.setattr(deps.importlib.util, "find_spec", boom)
        assert deps._vendors_gdal() is False, "find_spec error -> False"


class TestVendoredGdalWarningVersionAware:
    """Tests for the version-aware branch of ``vendored_gdal_warning``."""

    def test_none_when_vendored_but_new_enough(self, monkeypatch):
        """A vendored build >= the floor is safe (honours the env opt-out) -> no warning."""
        monkeypatch.setattr(deps, "_vendors_gdal", lambda: True)
        monkeypatch.setattr(deps, "pyramids_version", lambda: (0, 81, 0))
        assert deps.vendored_gdal_warning() is None, ">=0.81.0 vendored should not warn"

    def test_warns_when_vendored_and_outdated(self, monkeypatch):
        """A vendored build below the floor warns and names the required version."""
        monkeypatch.setattr(deps, "_vendors_gdal", lambda: True)
        monkeypatch.setattr(deps, "pyramids_version", lambda: (0, 79, 0))
        message = deps.vendored_gdal_warning()
        assert message is not None, "outdated vendored build should warn"
        assert "0.81.0" in message, f"warning should name the floor: {message}"

    def test_warns_when_vendored_and_version_unknown(self, monkeypatch):
        """A vendored build whose version cannot be read is treated conservatively (warn)."""
        monkeypatch.setattr(deps, "_vendors_gdal", lambda: True)
        monkeypatch.setattr(deps, "pyramids_version", lambda: None)
        assert deps.vendored_gdal_warning() is not None, (
            "unknown-version vendored build should warn"
        )

    def test_none_when_not_vendored(self, monkeypatch):
        """A non-vendored build never warns, regardless of version."""
        monkeypatch.setattr(deps, "_vendors_gdal", lambda: False)
        assert deps.vendored_gdal_warning() is None, "non-vendored -> no warning"


class TestPythonExecutable:
    """Tests for the ``_python_executable`` interpreter probe."""

    def test_returns_sys_executable_when_python(self, monkeypatch):
        """When sys.executable already looks like python, return it unchanged."""
        monkeypatch.setattr(deps.sys, "executable", "/usr/bin/python3.12")
        assert deps._python_executable() == "/usr/bin/python3.12", "a python exe is returned as-is"

    def test_probes_prefix_when_executable_is_not_python(self, tmp_path, monkeypatch):
        """When sys.executable is not python (QGIS binary), find python under a prefix's bin.

        Creates every candidate name so the test passes whatever the host's ``os.name`` picks
        (``python3.exe`` / ``python.exe`` on Windows, ``python3`` / ``python`` elsewhere); it does
        not monkeypatch ``os.name`` because that also steers ``pathlib`` and breaks on the other OS.
        """
        (tmp_path / "bin").mkdir()
        for name in ("python3.exe", "python.exe", "python3", "python"):
            (tmp_path / "bin" / name).write_text("")
        monkeypatch.setattr(deps.sys, "executable", str(tmp_path / "qgis-bin"))
        monkeypatch.setattr(deps.sys, "exec_prefix", str(tmp_path))
        monkeypatch.setattr(deps.sys, "base_prefix", str(tmp_path))
        result = Path(deps._python_executable())
        assert result.parent.name == "bin", f"expected a python under bin, got {result}"
        assert result.name.startswith("python"), f"expected a python executable, got {result.name}"

    def test_falls_back_to_executable_when_nothing_found(self, tmp_path, monkeypatch):
        """With no python under any prefix, fall back to sys.executable."""
        fake_exe = str(tmp_path / "qgis-bin")
        monkeypatch.setattr(deps.sys, "executable", fake_exe)
        monkeypatch.setattr(deps.sys, "exec_prefix", str(tmp_path))
        monkeypatch.setattr(deps.sys, "base_prefix", str(tmp_path))
        assert deps._python_executable() == fake_exe, "fallback is the original executable"


class _Completed:
    """Minimal stand-in for ``subprocess.CompletedProcess``."""

    def __init__(self, returncode, stdout="", stderr=""):
        """Store the fields ``install_pyramids`` reads."""
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestInstallPyramids:
    """Tests for ``install_pyramids`` (subprocess mocked — no real pip)."""

    def test_success_returns_true_and_output(self, monkeypatch):
        """A zero return code yields (True, combined output)."""
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        monkeypatch.setattr(deps.subprocess, "run", lambda *a, **k: _Completed(0, "installed ok"))
        ok, output = deps.install_pyramids()
        assert ok is True, "returncode 0 -> success"
        assert "installed ok" in output, f"stdout should be surfaced: {output}"

    def test_failure_returns_false_and_output(self, monkeypatch):
        """A non-zero return code yields (False, combined output)."""
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        monkeypatch.setattr(deps.subprocess, "run", lambda *a, **k: _Completed(1, "", "pip boom"))
        ok, output = deps.install_pyramids()
        assert ok is False, "non-zero returncode -> failure"
        assert "pip boom" in output, f"stderr should be surfaced: {output}"

    def test_upgrade_adds_flag(self, monkeypatch):
        """``upgrade=True`` puts --upgrade in the pip command."""
        captured = {}
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")

        def fake_run(command, **kwargs):
            captured["command"] = command
            return _Completed(0)

        monkeypatch.setattr(deps.subprocess, "run", fake_run)
        deps.install_pyramids(upgrade=True)
        assert "--upgrade" in captured["command"], f"missing --upgrade: {captured['command']}"

    def test_default_omits_upgrade_flag(self, monkeypatch):
        """Without ``upgrade`` the command has no --upgrade."""
        captured = {}
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")

        def fake_run(command, **kwargs):
            captured["command"] = command
            return _Completed(0)

        monkeypatch.setattr(deps.subprocess, "run", fake_run)
        deps.install_pyramids()
        assert "--upgrade" not in captured["command"], (
            f"unexpected --upgrade: {captured['command']}"
        )
        assert deps.PYRAMIDS_REQUIREMENT in captured["command"], (
            "requirement must be in the command"
        )

    def test_never_raises_on_launch_failure(self, monkeypatch):
        """A subprocess launch error is returned as a failure, never raised."""
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")

        def boom(*args, **kwargs):
            raise OSError("pip not found")

        monkeypatch.setattr(deps.subprocess, "run", boom)
        ok, output = deps.install_pyramids()
        assert ok is False, "a launch error is a failure, not an exception"
        assert "install manually" in output.lower(), f"should offer the manual command: {output}"
