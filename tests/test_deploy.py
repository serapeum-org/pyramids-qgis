"""Tests for the deploy helper's QGIS-profile path resolution (QGIS3 vs QGIS4)."""

from __future__ import annotations

from pathlib import Path

import deploy  # scripts/ is on the pytest pythonpath
import pytest


@pytest.fixture
def fake_plugin_src(tmp_path, monkeypatch):
    """Point ``deploy._PLUGIN_SRC`` at a throwaway plugin package and return its path.

    The fake carries ``metadata.txt`` and a ``__pycache__`` so copy tests can assert both the
    payload is copied and the ignore patterns are honoured.
    """
    src = tmp_path / "src_pkg"
    src.mkdir()
    (src / "metadata.txt").write_text("name=Pyramids QGIS\n", encoding="utf-8")
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "x.pyc").write_text("", encoding="utf-8")
    monkeypatch.setattr(deploy, "_PLUGIN_SRC", src)
    return src


def test_detect_prefers_qgis4_when_both_present(tmp_path):
    """Both generations installed → the newest (QGIS4) is chosen."""
    (tmp_path / "QGIS3").mkdir()
    (tmp_path / "QGIS4").mkdir()
    assert deploy._detect_qgis_dir(tmp_path) == "QGIS4"


def test_detect_falls_back_to_qgis3_when_only_qgis3(tmp_path):
    """Only a QGIS 3 tree present → deploy there, not into a non-existent QGIS4."""
    (tmp_path / "QGIS3").mkdir()
    assert deploy._detect_qgis_dir(tmp_path) == "QGIS3"


def test_detect_defaults_to_newest_when_none_present(tmp_path):
    """Fresh machine (no profile tree yet) → the newest known generation."""
    assert deploy._detect_qgis_dir(tmp_path) == "QGIS4"


def test_default_plugins_dir_autodetects_qgis4(tmp_path, monkeypatch):
    """Auto-detects the QGIS4 tree when present (regression: the path was hardcoded to QGIS3)."""
    (tmp_path / "QGIS4").mkdir()
    monkeypatch.setattr(deploy, "_qgis_config_base", lambda: tmp_path)
    result = deploy.default_plugins_dir("default")
    assert result == tmp_path / "QGIS4" / "profiles" / "default" / "python" / "plugins"


def test_default_plugins_dir_explicit_generation(tmp_path, monkeypatch):
    """An explicit qgis_dir overrides auto-detection."""
    (tmp_path / "QGIS4").mkdir()
    monkeypatch.setattr(deploy, "_qgis_config_base", lambda: tmp_path)
    result = deploy.default_plugins_dir("default", "QGIS3")
    assert result.parts[-5:] == ("QGIS3", "profiles", "default", "python", "plugins")


def test_default_plugins_dir_rejects_unknown_generation(tmp_path, monkeypatch):
    """A bogus generation is rejected rather than silently building a wrong path."""
    monkeypatch.setattr(deploy, "_qgis_config_base", lambda: tmp_path)
    with pytest.raises(ValueError, match="invalid QGIS generation"):
        deploy.default_plugins_dir("default", "QGIS9")


@pytest.mark.parametrize("bad", [".", "..", "", "a/b", "a\\b", "../../etc"])
def test_default_plugins_dir_rejects_unsafe_profile(bad):
    """Unsafe profile names are rejected with ValueError.

    `.` and `..` pass the ``_PROFILE_RE`` regex (``.`` is in the class), so the explicit
    ``profile in {".", ".."}`` membership check is the only guard against them — this keeps that
    branch covered. ``""`` and names with ``/`` or ``\\`` separators are rejected by the regex.
    """
    with pytest.raises(ValueError, match="invalid QGIS profile name"):
        deploy.default_plugins_dir(bad)


def test_config_base_windows(tmp_path, monkeypatch):
    """On Windows the config base is %APPDATA%/QGIS."""
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert deploy._qgis_config_base() == tmp_path / "Roaming" / "QGIS"


def test_config_base_macos(tmp_path, monkeypatch):
    """On macOS the config base is ~/Library/Application Support/QGIS."""
    monkeypatch.setattr("platform.system", lambda: "Darwin")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert deploy._qgis_config_base() == tmp_path / "Library" / "Application Support" / "QGIS"


def test_config_base_linux(tmp_path, monkeypatch):
    """On other systems the config base is ~/.local/share/QGIS."""
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert deploy._qgis_config_base() == tmp_path / ".local" / "share" / "QGIS"


def test_deploy_copy_installs_and_ignores_pycache(tmp_path, fake_plugin_src):
    """A copy deploy installs the package and omits __pycache__/*.pyc."""
    target = deploy.deploy(tmp_path / "plugins", symlink=False)
    assert target == (tmp_path / "plugins" / "pyramids_qgis").resolve()
    assert (target / "metadata.txt").is_file()
    assert not (target / "__pycache__").exists()


def test_deploy_copy_replaces_existing_dir(tmp_path, fake_plugin_src):
    """An existing plugin directory is removed before the fresh copy is written."""
    plugins = tmp_path / "plugins"
    stale = plugins / "pyramids_qgis"
    stale.mkdir(parents=True)
    (stale / "stale.txt").write_text("old", encoding="utf-8")
    target = deploy.deploy(plugins, symlink=False)
    assert not (target / "stale.txt").exists()
    assert (target / "metadata.txt").is_file()


def test_deploy_replaces_existing_file(tmp_path, fake_plugin_src):
    """An existing file at the target path is unlinked before deploying."""
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    (plugins / "pyramids_qgis").write_text("not a dir", encoding="utf-8")
    target = deploy.deploy(plugins, symlink=False)
    assert (target / "metadata.txt").is_file()


def test_deploy_symlink_invokes_symlink_to(tmp_path, fake_plugin_src, monkeypatch):
    """A symlink deploy calls Path.symlink_to with the plugin source (no real symlink needed)."""
    calls = {}

    def fake_symlink_to(self, source, target_is_directory=False):
        calls["self"] = self
        calls["source"] = source

    monkeypatch.setattr(Path, "symlink_to", fake_symlink_to)
    target = deploy.deploy(tmp_path / "plugins", symlink=True)
    assert calls["source"] == fake_plugin_src
    assert calls["self"] == target


def test_deploy_symlink_oserror_is_wrapped(tmp_path, fake_plugin_src, monkeypatch):
    """A symlink OSError becomes a RuntimeError with an actionable Windows hint."""

    def boom(self, source, target_is_directory=False):
        raise OSError("WinError 1314")

    monkeypatch.setattr(Path, "symlink_to", boom)
    with pytest.raises(RuntimeError, match="Developer Mode"):
        deploy.deploy(tmp_path / "plugins", symlink=True)


def test_main_copy_success(tmp_path, fake_plugin_src, capsys):
    """main() with --plugins-dir copies the plugin and returns 0."""
    rc = deploy.main(["--plugins-dir", str(tmp_path / "plugins")])
    assert rc == 0
    assert "copied pyramids_qgis" in capsys.readouterr().out
    assert (tmp_path / "plugins" / "pyramids_qgis" / "metadata.txt").is_file()


def test_main_qgis_version_routes_to_generation(tmp_path, fake_plugin_src, monkeypatch, capsys):
    """--qgis-version 4 deploys under the QGIS4 profile tree (no --plugins-dir)."""
    monkeypatch.setattr(deploy, "_qgis_config_base", lambda: tmp_path)
    rc = deploy.main(["--qgis-version", "4"])
    assert rc == 0
    expected = tmp_path / "QGIS4" / "profiles" / "default" / "python" / "plugins"
    assert "copied pyramids_qgis" in capsys.readouterr().out
    assert (expected / "pyramids_qgis" / "metadata.txt").is_file()


def test_main_missing_source_returns_1(tmp_path, monkeypatch, capsys):
    """main() returns 1 with a clear message when the plugin source is absent."""
    monkeypatch.setattr(deploy, "_PLUGIN_SRC", tmp_path / "nope")
    rc = deploy.main(["--plugins-dir", str(tmp_path / "plugins")])
    assert rc == 1
    assert "plugin source not found" in capsys.readouterr().err


def test_main_deploy_error_returns_1(tmp_path, fake_plugin_src, monkeypatch, capsys):
    """A deploy failure is reported as a one-line error and a non-zero exit."""

    def boom(plugins_dir, *, symlink):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(deploy, "deploy", boom)
    rc = deploy.main(["--plugins-dir", str(tmp_path / "plugins")])
    assert rc == 1
    assert "error: disk on fire" in capsys.readouterr().err


def test_main_no_flags_autodetects_generation(tmp_path, fake_plugin_src, monkeypatch, capsys):
    """`main([])` (bare `python scripts/deploy.py`) auto-detects the newest present generation.

    This drives the ``qgis_dir = ... if args.qgis_version else None`` else-branch — the no-flag
    auto-detect path that is the exact regression this PR fixes — which coverage.py does not
    arc-split out of the ternary.
    """
    (tmp_path / "QGIS4").mkdir()
    monkeypatch.setattr(deploy, "_qgis_config_base", lambda: tmp_path)
    rc = deploy.main([])
    assert rc == 0
    target = tmp_path / "QGIS4" / "profiles" / "default" / "python" / "plugins" / "pyramids_qgis"
    assert (target / "metadata.txt").is_file()
    assert "copied pyramids_qgis" in capsys.readouterr().out
