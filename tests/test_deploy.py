"""Unit tests for ``scripts/deploy.py`` — pure stdlib, no QGIS needed.

The deploy helper copies or symlinks the plugin package into a QGIS profile. These tests exercise
the copy path, the platform-specific plugins-directory resolution, and the L3 fix that turns a
Windows symlink ``OSError`` into a clean ``RuntimeError``.
"""

from __future__ import annotations

import deploy
import pytest


def test_deploy_copy_installs_the_package(tmp_path):
    """Copying lays the plugin down at <dir>/pyramids_qgis and excludes __pycache__."""
    target = deploy.deploy(tmp_path, symlink=False)
    assert target == tmp_path / "pyramids_qgis"
    assert (target / "__init__.py").is_file()
    assert (target / "algorithms" / "base.py").is_file()
    assert not any(p.name == "__pycache__" for p in target.rglob("*"))


def test_deploy_copy_replaces_an_existing_install(tmp_path):
    """A copy over a pre-existing target directory replaces it rather than erroring."""
    target = tmp_path / "pyramids_qgis"
    target.mkdir()
    (target / "stale.txt").write_text("old")
    result = deploy.deploy(tmp_path, symlink=False)
    assert not (target / "stale.txt").exists()
    assert (result / "__init__.py").is_file()


def test_deploy_symlink_oserror_becomes_runtimeerror(tmp_path, monkeypatch):
    """A symlink OSError (e.g. Windows WinError 1314) is re-raised as a clean RuntimeError."""

    def boom(self, *args, **kwargs):
        raise OSError("WinError 1314")

    monkeypatch.setattr(deploy.Path, "symlink_to", boom)
    with pytest.raises(RuntimeError, match="symlink"):
        deploy.deploy(tmp_path, symlink=True)


@pytest.mark.parametrize(
    ("system", "tail"),
    [
        ("Linux", ".local/share/QGIS/QGIS3/profiles/default/python/plugins"),
        ("Darwin", "Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins"),
    ],
)
def test_default_plugins_dir_per_platform(monkeypatch, system, tail):
    """The plugins directory ends with the platform's QGIS profile path."""
    monkeypatch.setattr(deploy.platform, "system", lambda: system)
    assert deploy.default_plugins_dir("default").as_posix().endswith(tail)


def test_default_plugins_dir_windows_uses_appdata(monkeypatch):
    """On Windows the plugins directory is rooted at %APPDATA%\\QGIS\\QGIS3."""
    monkeypatch.setattr(deploy.platform, "system", lambda: "Windows")
    monkeypatch.setenv("APPDATA", str(deploy.Path("C:/Users/x/AppData/Roaming")))
    result = deploy.default_plugins_dir("myprofile").as_posix()
    assert result.endswith("QGIS/QGIS3/profiles/myprofile/python/plugins")
