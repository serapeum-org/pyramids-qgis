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


class _FakeQProcess:
    """Stand-in for ``QProcess``: records the argv and replays a scripted outcome.

    ``install_pyramids`` imports ``QProcess`` lazily from ``qgis.PyQt.QtCore``, so tests patch the
    name on that module and get this class instead. Only the handful of methods the function calls
    are implemented; anything else is a deliberate AttributeError.
    """

    #: Every instance built since the last patch, so a test can read back the argv.
    created: list = []

    #: Script applied to each new instance, set by :func:`_patch_process`.
    script: dict = {}

    def __init__(self):
        """Apply the current script and register the instance."""
        self.program = None
        self.argv = []
        self.start_called = False
        self.stdin_file = None
        self.killed = False
        self.start_timeout = None
        self.finish_timeout = None
        self._started = self.script.get("started", True)
        self._finished = self.script.get("finished", True)
        self._exit_code = self.script.get("exit_code", 0)
        self._stdout = self.script.get("stdout", b"")
        self._stderr = self.script.get("stderr", b"")
        type(self).created.append(self)

    def setProgram(self, program):  # noqa: N802 - Qt API name
        """Record the executable."""
        self.program = program

    def setArguments(self, arguments):  # noqa: N802 - Qt API name
        """Record the argument list."""
        self.argv = list(arguments)

    def setStandardInputFile(self, path):  # noqa: N802 - Qt API name
        """Record the file stdin was redirected from."""
        self.stdin_file = path

    @staticmethod
    def nullDevice():  # noqa: N802 - Qt API name
        """Return a sentinel standing in for Qt's platform null device."""
        return "<null-device>"

    def start(self):
        """Note that the process was launched."""
        self.start_called = True

    def waitForStarted(self, msecs):  # noqa: N802 - Qt API name
        """Report whether the launch succeeded, per the script."""
        self.start_timeout = msecs
        return self._started

    def waitForFinished(self, msecs):  # noqa: N802 - Qt API name
        """Report whether the run completed in time, per the script."""
        self.finish_timeout = msecs
        return self._finished

    def kill(self):
        """Note that the process was killed."""
        self.killed = True

    def readAllStandardOutput(self):  # noqa: N802 - Qt API name
        """Return the scripted stdout bytes."""
        return self._stdout

    def readAllStandardError(self):  # noqa: N802 - Qt API name
        """Return the scripted stderr bytes."""
        return self._stderr

    def exitCode(self):  # noqa: N802 - Qt API name
        """Return the scripted exit code."""
        return self._exit_code

    def errorString(self):  # noqa: N802 - Qt API name
        """Return a fixed Qt-style launch error message."""
        return "No such file or directory"


def _patch_process(monkeypatch, **script):
    """Replace ``QProcess`` with :class:`_FakeQProcess` for one test.

    Args:
        monkeypatch: pytest's monkeypatch fixture.
        **script: Outcome to replay - ``started``, ``finished``, ``exit_code``, ``stdout``,
            ``stderr``.

    Returns:
        list: The (initially empty) list each constructed fake appends itself to, so the caller
            can assert on the argv afterwards.
    """
    _FakeQProcess.created = []
    _FakeQProcess.script = script
    monkeypatch.setattr("qgis.PyQt.QtCore.QProcess", _FakeQProcess)
    return _FakeQProcess.created


class TestReadAll:
    """Tests for ``_read_all``."""

    def test_decodes_utf8(self):
        """Bytes are decoded as UTF-8.

        Test scenario:
            ``b"installed ok"`` decodes to the same text.
        """
        assert deps._read_all(b"installed ok") == "installed ok", "utf-8 should round-trip"

    def test_replaces_undecodable_bytes(self):
        """Invalid bytes are replaced instead of raising.

        Test scenario:
            pip output under a non-UTF-8 console code page must not crash the installer.
        """
        out = deps._read_all(b"caf\xff")
        assert out.startswith("caf"), f"prefix should survive: {out!r}"
        assert "\ufffd" in out, f"bad byte should become U+FFFD: {out!r}"


class TestInstallPyramids:
    """Tests for ``install_pyramids`` (QProcess faked - no real pip runs)."""

    def test_success_returns_true_and_output(self, monkeypatch):
        """Exit code 0 yields (True, combined output).

        Test scenario:
            A process that starts, finishes and exits 0 with stdout is a success.
        """
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        _patch_process(monkeypatch, exit_code=0, stdout=b"installed ok")
        ok, output = deps.install_pyramids()
        assert ok is True, "exit code 0 -> success"
        assert "installed ok" in output, f"stdout should be surfaced: {output}"

    def test_failure_returns_false_and_output(self, monkeypatch):
        """A non-zero exit code yields (False, combined output).

        Test scenario:
            pip failing with a message on stderr is reported, not raised.
        """
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        _patch_process(monkeypatch, exit_code=1, stderr=b"pip boom")
        ok, output = deps.install_pyramids()
        assert ok is False, "non-zero exit code -> failure"
        assert "pip boom" in output, f"stderr should be surfaced: {output}"

    def test_runs_the_interpreter_with_pip_install(self, monkeypatch):
        """The program is the resolved interpreter and the argv is a pip install.

        Test scenario:
            argv must not repeat the executable - QProcess takes it via setProgram.
        """
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        created = _patch_process(monkeypatch)
        deps.install_pyramids()
        proc = created[0]
        assert proc.program == "py", f"program should be the interpreter: {proc.program}"
        assert proc.argv[:3] == ["-m", "pip", "install"], f"unexpected argv: {proc.argv}"
        assert proc.start_called, "the process must actually be started"

    def test_upgrade_adds_flag(self, monkeypatch):
        """``upgrade=True`` puts --upgrade in the argv.

        Test scenario:
            Used when an older pyramids is already installed.
        """
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        created = _patch_process(monkeypatch)
        deps.install_pyramids(upgrade=True)
        assert "--upgrade" in created[0].argv, f"missing --upgrade: {created[0].argv}"

    def test_default_omits_upgrade_flag(self, monkeypatch):
        """Without ``upgrade`` the argv has no --upgrade but does carry the requirement.

        Test scenario:
            A fresh install must not pass --upgrade, and must pin the version floor.
        """
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        created = _patch_process(monkeypatch)
        deps.install_pyramids()
        argv = created[0].argv
        assert "--upgrade" not in argv, f"unexpected --upgrade: {argv}"
        assert deps.PYRAMIDS_REQUIREMENT in argv, f"requirement must be in the argv: {argv}"

    def test_never_raises_on_launch_failure(self, monkeypatch):
        """A process that never starts is a failure carrying the manual command.

        Test scenario:
            Wrong interpreter path or missing pip - Qt reports it through waitForStarted() and
            errorString() rather than an exception, and the user still gets a command to run.
        """
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        _patch_process(monkeypatch, started=False)
        ok, output = deps.install_pyramids()
        assert ok is False, "a launch error is a failure, not an exception"
        assert "install manually" in output.lower(), f"should offer the manual command: {output}"
        assert "No such file" in output, f"Qt's errorString should be surfaced: {output}"

    def test_timeout_kills_the_process_and_reports(self, monkeypatch):
        """A run that outlasts the budget is killed and reported as a failure.

        Test scenario:
            waitForFinished() timing out must not leave the process running, and must still hand
            the user the manual command.
        """
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        created = _patch_process(monkeypatch, finished=False)
        ok, output = deps.install_pyramids()
        assert ok is False, "a timeout is a failure"
        assert created[0].killed, "a timed-out process must be killed, not abandoned"
        assert "install manually" in output.lower(), f"should offer the manual command: {output}"

    def test_timeouts_are_passed_in_milliseconds(self, monkeypatch):
        """The Qt waits receive the module's millisecond budgets.

        Test scenario:
            QProcess takes milliseconds while the old subprocess call took seconds; passing 600
            instead of 600_000 would cut a ten-minute budget to 0.6s.
        """
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        created = _patch_process(monkeypatch)
        deps.install_pyramids()
        proc = created[0]
        assert proc.start_timeout == deps.PIP_START_TIMEOUT_MS, "start budget must be in ms"
        assert proc.finish_timeout == deps.PIP_TIMEOUT_MS, "install budget must be in ms"
        assert deps.PIP_TIMEOUT_MS >= 600_000, "the install budget must stay at least 10 minutes"

    def test_child_stdin_is_closed(self, monkeypatch):
        """The child's stdin is redirected from the null device before it starts.

        Test scenario:
            ``QProcess.start()`` opens a pipe to the child's stdin and holds it open, where
            ``subprocess`` left stdin inherited (and therefore EOF in QGIS's console-less GUI
            process). Measured on real Qt6: a stdin-reading child launched without this call is
            still ``Running`` after 3s and would block for the whole budget, freezing the GUI;
            with it, the child finishes in 0.08s.
        """
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        created = _patch_process(monkeypatch)
        deps.install_pyramids()
        assert created[0].stdin_file == _FakeQProcess.nullDevice(), (
            f"stdin must be redirected from the null device, got {created[0].stdin_file!r}"
        )

    def test_pip_is_told_not_to_prompt(self, monkeypatch):
        """The argv carries --no-input so pip errors instead of waiting for a prompt.

        Test scenario:
            Belt and braces alongside the closed stdin: pip's keyring and proxy-auth paths prompt,
            and ``--no-input`` makes pip fail with a message that reaches the user through the
            existing output path instead of blocking.
        """
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        created = _patch_process(monkeypatch)
        deps.install_pyramids()
        assert "--no-input" in created[0].argv, f"missing --no-input: {created[0].argv}"

    def test_timeout_reports_the_partial_output(self, monkeypatch):
        """A timeout surfaces whatever pip had already written.

        Test scenario:
            Verified on real Qt6 that output written before a timeout is still readable after the
            kill: a child printing ``PARTIAL-PROGRESS`` then sleeping past the budget yields that
            text from ``readAllStandardOutput()``. The 10-minute budget only expires on a wedged
            install, which is exactly when the partial log ("Downloading GDAL-...whl (90 MB)") is
            the user's only diagnostic - so it must not be dropped.
        """
        monkeypatch.setattr(deps, "_python_executable", lambda: "py")
        _patch_process(monkeypatch, finished=False, stdout=b"PARTIAL-PROGRESS")
        ok, output = deps.install_pyramids()
        assert ok is False, "a timeout is still a failure"
        assert "PARTIAL-PROGRESS" in output, f"partial pip output must be kept: {output!r}"

    def test_manual_command_quotes_the_requirement(self, monkeypatch):
        """The manual command double-quotes the requirement and the interpreter path.

        Test scenario:
            ``>`` is a redirection operator in both cmd.exe and PowerShell, so an unquoted
            ``pyramids-core>=0.81.0`` pasted into a Windows shell runs ``pip install
            pyramids-core`` and writes stdout to a file - installing with **no version floor**,
            the one thing this module exists to enforce. Measured: cmd.exe created a file named
            ``0.81.0``. Single quotes do not help either (cmd created ``0.81.0'``); only double
            quotes do. The interpreter path needs them too - it is normally
            ``C:/Program Files/QGIS 4.2.2/...`` (a path that contains a space).
        """
        monkeypatch.setattr(deps, "_python_executable", lambda: r"C:\Program Files\QGIS\py.exe")
        _patch_process(monkeypatch, started=False)
        _, output = deps.install_pyramids()
        assert f'"{deps.PYRAMIDS_REQUIREMENT}"' in output, (
            f"the requirement must be double-quoted: {output!r}"
        )
        assert '"C:\\Program Files\\QGIS\\py.exe"' in output, (
            f"the interpreter path must be double-quoted: {output!r}"
        )


class TestInstallHintsAreShellSafe:
    """The module's other copy-paste install hints must survive a Windows shell too."""

    def test_install_hint_double_quotes_the_requirement(self):
        """``_INSTALL_HINT`` double-quotes the requirement.

        Test scenario:
            This is the string raised at users when pyramids-core is missing, so it is the most
            likely of all of them to be pasted into a shell.
        """
        assert f'"{deps.PYRAMIDS_REQUIREMENT}"' in deps._INSTALL_HINT, (
            f"single quotes do not protect >= in cmd.exe: {deps._INSTALL_HINT!r}"
        )

    def test_vendored_gdal_warning_double_quotes_the_requirement(self, monkeypatch):
        """The vendored-GDAL upgrade hint double-quotes the requirement.

        Test scenario:
            Same defect class as ``_INSTALL_HINT``. This hint tells the user to upgrade away from a
            GDAL-vendoring build that can clobber QGIS's GDAL, so a paste that drops the floor
            reinstalls the very build being warned about.
        """
        monkeypatch.setattr(deps, "_vendors_gdal", lambda: True)
        monkeypatch.setattr(deps, "pyramids_version", lambda: (0, 1, 0))
        message = deps.vendored_gdal_warning()
        assert message is not None, "an old vendored build must produce a warning"
        assert f'"{deps.PYRAMIDS_REQUIREMENT}"' in message, (
            f"single quotes do not protect >= in cmd.exe: {message!r}"
        )
