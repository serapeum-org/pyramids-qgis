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


def test_deploy_copy_replaces_an_existing_file_target(tmp_path):
    """A plain file sitting where the package goes is unlinked and replaced by the copy."""
    (tmp_path / "pyramids_qgis").write_text("stale file, not a dir")
    target = deploy.deploy(tmp_path, symlink=False)
    assert target.is_dir()
    assert (target / "__init__.py").is_file()


def test_main_copy_returns_zero(tmp_path, monkeypatch, capsys):
    """`main` deploys to the resolved plugins dir and reports success (exit 0)."""
    monkeypatch.setattr(deploy, "default_plugins_dir", lambda profile: tmp_path)
    assert deploy.main([]) == 0
    assert (tmp_path / "pyramids_qgis" / "__init__.py").is_file()
    assert "copied pyramids_qgis" in capsys.readouterr().out


def test_main_explicit_plugins_dir_overrides_profile(tmp_path, monkeypatch, capsys):
    """`--plugins-dir` wins over `--profile` for the deploy target."""

    def unexpected(profile):
        raise AssertionError("default_plugins_dir must not be called when --plugins-dir is given")

    monkeypatch.setattr(deploy, "default_plugins_dir", unexpected)
    assert deploy.main(["--plugins-dir", str(tmp_path)]) == 0
    assert (tmp_path / "pyramids_qgis").is_dir()


def test_main_missing_plugin_source_returns_one(tmp_path, monkeypatch, capsys):
    """`main` exits 1 with a message when the plugin source does not exist."""
    monkeypatch.setattr(deploy, "_PLUGIN_SRC", tmp_path / "does-not-exist")
    assert deploy.main([]) == 1
    assert "plugin source not found" in capsys.readouterr().err


def test_main_reports_symlink_failure_as_exit_one(tmp_path, monkeypatch, capsys):
    """A RuntimeError from deploy (e.g. blocked symlink) is reported and exits 1."""
    monkeypatch.setattr(deploy, "default_plugins_dir", lambda profile: tmp_path)

    def boom(plugins_dir, *, symlink):
        raise RuntimeError("could not create a symlink")

    monkeypatch.setattr(deploy, "deploy", boom)
    assert deploy.main(["--symlink"]) == 1
    assert "could not create a symlink" in capsys.readouterr().err


def test_main_reports_copy_oserror_as_exit_one(tmp_path, monkeypatch, capsys):
    """An OSError from the copy path (locked/read-only destination) is reported and exits 1."""
    monkeypatch.setattr(deploy, "default_plugins_dir", lambda profile: tmp_path)

    def boom(plugins_dir, *, symlink):
        raise OSError("WinError 5 access denied")

    monkeypatch.setattr(deploy, "deploy", boom)
    assert deploy.main([]) == 1
    assert "access denied" in capsys.readouterr().err


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
