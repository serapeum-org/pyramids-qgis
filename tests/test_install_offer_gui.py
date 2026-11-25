"""Tests that drive the real ``pyramids-core`` install dialog, offscreen.

The offer is the plugin's most user-visible code and was previously untestable: it opens a **modal**
``QMessageBox`` (``plugin.py``, ``box.exec()``), and ``exec()`` does not return until something
clicks a button, so a test could never reach them from its own body.

The way in is to arm the interaction *before* triggering the modal. :class:`DialogDriver` starts a
repeating ``QTimer`` which, from inside ``exec()``'s own nested event loop, finds the open dialog
and clicks a button, so ``exec()`` returns normally. That needs no extra test dependency — only the
session ``QgsApplication`` the suite already builds and the ``QT_QPA_PLATFORM=offscreen`` platform
``conftest`` already sets, so these run headless on both Qt5 and Qt6.

Five details are load-bearing, each of them learned by running it:

- The driver **polls** rather than scheduling one handler per dialog at a fixed offset. Accepting
  the offer opens a **second** modal — the outcome dialog — which does not exist until the first is
  answered, so fixed offsets race it.
- ``_run_install_offer`` imports ``install_pyramids`` from :mod:`pyramids_qgis.dependencies` *as it
  runs*, so a stub must replace the attribute on that module. Patching it on
  :mod:`pyramids_qgis.plugin` has no effect, and the real installer would run ``pip``. Every test
  that reaches the offer therefore takes a fixture that stubs it; the few driver-only tests never
  get as far as an install.
- ``QMessageBox`` has no ``buttonText()`` method, and has not since Qt 5.0, so this is not a Qt6
  difference. Buttons come from ``box.buttons()``; a standard button is matched by its
  ``QMessageBox.StandardButton`` enum rather than its text, which Qt translates, and a custom button
  by the exact text the plugin gave it.
- **Nothing may escape a Qt timer slot.** An exception there does not fail a test, it aborts the
  interpreter — observed as exit ``0xC0000409``, with no traceback and no pytest summary. Every tick
  is wrapped, and a dialog the driver cannot answer is force-closed. A modal that refuses to close
  is reported rather than waited on, and the :func:`hang_watchdog` fixture bounds the rest with
  ``faulthandler``: a stuck test ends the run with exit code 1 within
  :data:`WATCHDOG_SECONDS` instead of burning the CI job's whole time limit. It uses the standard
  library on purpose — ``pytest-timeout`` would be a new dependency and therefore a re-locked
  ``pixi.lock``, which CI installs with ``--locked``.
- ``QApplication.activeModalWidget()`` can be ``None`` while a modal really is open, so
  :func:`_open_modal` falls back to scanning ``topLevelWidgets()``. This matters more than it looks:
  a driver that gives up *without closing* the dialog leaves ``exec()`` spinning, so the test body
  is never reached, nothing is reported, and the CI job runs to its own timeout. For the same reason
  :meth:`DialogDriver._force_close` walks the widget list itself instead of reusing that lookup —
  the last resort must not depend on the thing that failed.

:attr:`DialogDriver.ticks` and :attr:`DialogDriver.pending` exist so a test can show the driver was
armed and polling: asserting only "no dialog appeared" would pass just as well against a driver that
never ran. ``ticks`` counts from the most recent :meth:`DialogDriver.expect`, and the queue is
answered strictly in order, which assumes the dialogs appear one at a time — true of this plugin,
where the outcome dialog only opens after the offer is answered.
"""

from __future__ import annotations

import faulthandler
import html

import pytest
from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QEventLoop, Qt, QTimer
from qgis.PyQt.QtWidgets import QApplication, QDialog, QMessageBox, QWidget

from pyramids_qgis import dependencies as deps
from pyramids_qgis.plugin import INSTALL_OFFER_DISMISSED_KEY, PyramidsPlugin

#: ``gui`` selects these specifically; ``integration`` is also applied because they need a real
#: QGIS install, so ``-m "not integration"`` skips them along with the other heavy tests.
pytestmark = [pytest.mark.gui, pytest.mark.integration]

#: How many poll ticks to wait for the whole queue before giving up and closing what is open. It is
#: one budget for the arming, not one per dialog. Counted in ticks rather than wall clock, because
#: only a running event loop advances them, so a slow runner cannot trip it early.
RESCUE_TICKS = 160

#: How often to look for an open dialog while a queue is outstanding, in milliseconds.
POLL_MS = 25

#: How many close passes to make before reporting that a modal will not go away.
ROUNDS_TO_CLOSE = 5

#: How long any one test in this module may run before the watchdog dumps a traceback and exits.
#: Generous: it is a backstop for a hang, not a performance budget (the whole module runs in ~6s).
WATCHDOG_SECONDS = 90.0

#: The standard buttons the plugin uses, keyed by the label a test asks for. Matching by enum keeps
#: these tests working under a translated Qt, where "Yes" and "OK" are localised.
STANDARD_BUTTONS = {
    "Yes": QMessageBox.StandardButton.Yes,
    "OK": QMessageBox.StandardButton.Ok,
}


def _plain(text: str) -> str:
    """Return ``text`` without Qt's mnemonic markers.

    A single ``&`` marks the next character as the accelerator; a doubled ``&&`` is how Qt escapes a
    literal ampersand, so the two cases cannot both be handled by stripping every ``&``.

    Args:
        text: A button's label as Qt reports it.

    Returns:
        str: The label as a user sees it.
    """
    return text.replace("&&", "\x00").replace("&", "").replace("\x00", "&")


def _modal_widgets() -> list[QWidget]:
    """Return every visible modal top-level widget, most recently shown first.

    Not just ``QDialog``: a ``QMenu`` also runs its own modal loop, and anything with a modal loop
    can block ``exec()`` from returning. Only *modal* widgets are included — a non-modal dialog may
    belong to QGIS or another fixture, and closing it is not this driver's business.

    Returns:
        list[QWidget]: The open modal widgets, with ``activeModalWidget()`` first when it has one.
    """
    found: list[QWidget] = []
    active = QApplication.activeModalWidget()
    if active is not None:
        found.append(active)
    for widget in QApplication.topLevelWidgets():
        if widget not in found and widget.isVisible() and widget.isModal():
            found.append(widget)
    return found


def _open_modal():
    """Return the modal widget to answer next, or ``None``.

    ``QApplication.activeModalWidget()`` is the normal answer, but it can be ``None`` while a modal
    is genuinely open; the top-level scan is the fallback that keeps the driver — and therefore the
    whole run — from waiting forever on a dialog it cannot see.

    Returns:
        QWidget | None: The open modal widget, preferring the active one.
    """
    widgets = _modal_widgets()
    return widgets[0] if widgets else None


class DialogDriver:
    """Answers a scripted queue of modal dialogs and records what it saw.

    Attributes:
        seen: One record per dialog answered, holding its ``title``, the visible ``buttons``, the
            full ``text``, its ``format`` (rich or plain), the label that was ``requested`` and the
            ``clicked`` button's own text, so a lenient match cannot hide which button was pressed.
        errors: Why a dialog could not be answered as scripted, including rescues and anything
            raised inside the timer slot.
        ticks: How many times the poll timer ran. A test asserting that no dialog appeared uses this
            to prove the driver was actually alive.
    """

    def __init__(self) -> None:
        """Start with nothing seen, nothing queued and no timer running."""
        self.seen: list[dict[str, object]] = []
        self.errors: list[str] = []
        self.ticks = 0
        self._queue: list[str] = []
        self._timer: QTimer | None = None

    @property
    def pending(self) -> list[str]:
        """Return the labels still waiting for a dialog, so a test can assert the queue drained."""
        return list(self._queue)

    @property
    def titles(self) -> list[str]:
        """Return the window titles of the dialogs answered, in order."""
        return [str(record["title"]) for record in self.seen]

    def expect(self, *labels: str) -> None:
        """Queue one label per dialog, to be clicked as each dialog appears.

        Args:
            labels: One label per expected dialog, in order. ``"Yes"`` and ``"OK"`` match the
                standard buttons by enum; any other label matches a custom button's exact text.
        """
        self.stop()
        self._queue = list(labels)
        self.ticks = 0
        self._timer = QTimer()
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def stop(self) -> None:
        """Stop polling. Called by :meth:`expect` and at teardown, so no timer outlives its test."""
        if self._timer is not None:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None

    def _tick(self) -> None:
        """Answer the open dialog, if any — and never let anything escape into the Qt slot."""
        try:
            self.ticks += 1
            box = _open_modal()
            if box is not None and self._queue:
                self._answer(box, self._queue.pop(0))
            if not self._queue:
                self.stop()
                if _modal_widgets():
                    # A dialog the queue did not account for, or one that ignored its own close:
                    # leaving it open means exec() never returns and the run dies by job timeout.
                    self.errors.append("a modal was still open once the queue drained")
                    self._safe_force_close()
                return
            if self.ticks >= RESCUE_TICKS:
                self.errors.append(f"gave up waiting for dialogs; still expecting {self._queue}")
                self._queue.clear()
                self.stop()
                self._safe_force_close()
        except BaseException as error:  # noqa: BLE001  (a raise here aborts the interpreter)
            # Even recording the failure has to be defensive: an exception escaping this handler is
            # not a failed test, it is a dead process with no traceback and no pytest summary.
            try:
                self.errors.append(f"{type(error).__name__} in the timer slot: {error}")
                self._queue.clear()
                self.stop()
            finally:
                self._safe_force_close()

    def _answer(self, box: QWidget, label: str) -> None:
        """Click the button of ``box`` matching ``label``.

        Args:
            box: The modal dialog currently open. A dialog that is not a ``QMessageBox`` has no
                buttons to click, so it is recorded and closed rather than crashed into.
            label: A key of :data:`STANDARD_BUTTONS`, or the exact text of a custom button.
        """
        if not isinstance(box, QMessageBox):
            self.errors.append(
                f"not a message box: expected buttons for {label!r}, got {type(box).__name__}"
            )
            if isinstance(box, QDialog):
                box.reject()
            box.close()
            return
        buttons = list(box.buttons())
        labels = [_plain(button.text()) for button in buttons]
        target = next((b for b in buttons if _plain(b.text()) == label), None)
        if target is None and label in STANDARD_BUTTONS:
            wanted = STANDARD_BUTTONS[label]
            target = next((b for b in buttons if box.standardButton(b) == wanted), None)
        self.seen.append(
            {
                "title": box.windowTitle(),
                "buttons": labels,
                "text": box.text(),
                "format": box.textFormat(),
                "requested": label,
                "clicked": _plain(target.text()) if target is not None else None,
            }
        )
        if target is None:
            self.errors.append(f"no button {label!r} among {sorted(labels)}")
            box.reject()
            return
        target.click()

    def _safe_force_close(self) -> None:
        """Run :meth:`_force_close` without letting it raise into the timer slot."""
        try:
            self._force_close()
        except BaseException as error:  # noqa: BLE001  (see _tick: a raise here kills the process)
            self.errors.append(f"{type(error).__name__} while force-closing: {error}")

    def _force_close(self) -> None:
        """Close every open modal, so ``exec()`` returns and the test body is reached.

        Rejecting only ``activeModalWidget()`` is not enough: it is ``None`` in exactly the case the
        rescue exists for, and skipping the close leaves ``exec()`` spinning until the CI job's own
        timeout kills the run with no output at all. It therefore scans for modal widgets itself
        rather than reusing the lookup that may have failed.

        Only *modal* widgets are closed: a visible non-modal dialog can belong to QGIS or another
        fixture, and rejecting it would fire its ``rejected`` signal behind its owner's back.
        """
        for _ in range(ROUNDS_TO_CLOSE):
            widgets = _modal_widgets()
            if not widgets:
                return
            for widget in widgets:
                if isinstance(widget, QDialog):
                    widget.reject()
                widget.close()
        remaining = [type(widget).__name__ for widget in _modal_widgets()]
        if remaining:
            # Nothing else can be done from Python; say so, because the alternative is a silent
            # hang that only shows up as a job timeout with no output.
            self.errors.append(
                f"modal(s) refused to close after {ROUNDS_TO_CLOSE} rounds: {remaining}"
            )


@pytest.fixture(autouse=True)
def hang_watchdog():
    """Abort with a traceback if a test in this module runs far longer than it should.

    These tests drive modal dialogs, where the failure mode is not an assertion but a hang: a modal
    that never closes leaves ``exec()`` spinning, the test body is never reached, nothing is
    reported, and CI eventually kills the job with no output. ``faulthandler`` turns that into a
    dumped traceback that names the stuck frame.

    It is the standard library rather than ``pytest-timeout`` deliberately: a new dependency would
    invalidate the committed ``pixi.lock``, which CI installs with ``--locked``.

    What this does and does not buy, measured rather than assumed: with the fallback scan broken on
    purpose, the run ended at the watchdog with **exit code 1** instead of hanging, so CI reports a
    failure. The traceback itself did **not** survive — pytest captures at the file-descriptor level
    and ``os._exit`` discards that buffer — and a two-stage dump-then-exit variant did not change
    that, so it was dropped rather than kept for show. Attribution therefore comes from the last
    test to print its dot, plus :attr:`DialogDriver.errors`, which the in-suite rescues populate
    before any of this is reached.
    """
    faulthandler.dump_traceback_later(WATCHDOG_SECONDS, exit=True)
    try:
        yield
    finally:
        faulthandler.cancel_dump_traceback_later()


@pytest.fixture
def transient_modal():
    """Return a factory for modal widgets that are destroyed when the test ends.

    A parentless widget otherwise stays in ``QApplication.topLevelWidgets()`` for the rest of the
    session, where the driver's own scan would keep finding it.

    Returns:
        Callable[[QWidget], QWidget]: Registers the widget for cleanup and hands it back.
    """
    created: list[QWidget] = []

    def register(widget: QWidget) -> QWidget:
        """Remember ``widget`` for destruction at teardown and return it unchanged."""
        created.append(widget)
        return widget

    yield register
    for widget in created:
        widget.close()
        widget.deleteLater()


@pytest.fixture
def driver():
    """Yield a fresh :class:`DialogDriver`, and stop it however the test ends.

    Without the teardown a timer from a failed test keeps polling and answers the *next* test's
    dialog, which turns one real failure into a cascade of misleading ones.
    """
    helper = DialogDriver()
    yield helper
    helper.stop()
    helper._force_close()


@pytest.fixture
def clean_dismissal():
    """Restore the recorded decline around a test, rather than deleting it.

    ``QgsSettings`` is process-wide and shared with whatever profile the suite runs against, so the
    previous value is put back instead of being dropped.
    """
    previous = QgsSettings().value(INSTALL_OFFER_DISMISSED_KEY, None)
    QgsSettings().remove(INSTALL_OFFER_DISMISSED_KEY)
    yield
    if previous is None:
        QgsSettings().remove(INSTALL_OFFER_DISMISSED_KEY)
    else:
        QgsSettings().setValue(INSTALL_OFFER_DISMISSED_KEY, previous)


@pytest.fixture
def installs(monkeypatch):
    """Stub the installer on the module the offer imports it from, and record its calls.

    Returns:
        list[dict]: The keyword arguments of each ``install_pyramids`` call, empty until something
        accepts the offer. Taking this fixture is what guarantees a test cannot run real ``pip``.
    """
    calls: list[dict] = []

    def fake_install(**kwargs):
        """Record the call and report success without running pip."""
        calls.append(kwargs)
        return True, "stubbed installer: no pip ran"

    monkeypatch.setattr(deps, "install_pyramids", fake_install)
    return calls


@pytest.fixture
def becomes_installed(monkeypatch):
    """Stub a successful install that actually makes ``pyramids-core`` importable afterwards.

    The offer must first see pyramids as missing and the outcome dialog must then see it as present,
    which is what a real successful install looks like. A flag flipped by the stubbed installer
    models that, so the success branch of ``_report_install_result`` is reachable at all.

    Returns:
        list[dict]: The keyword arguments of each install call, for assertions.
    """
    calls: list[dict] = []
    installed = {"yes": False}

    def fake_install(**kwargs):
        """Record the call, mark pyramids importable, and report success without running pip."""
        calls.append(kwargs)
        installed["yes"] = True
        return True, "stubbed installer: no pip ran"

    monkeypatch.setattr(deps, "install_pyramids", fake_install)
    monkeypatch.setattr(deps, "pyramids_installed", lambda: installed["yes"])
    monkeypatch.setattr(deps, "pyramids_outdated", lambda: False)
    return calls


@pytest.fixture
def missing_pyramids(monkeypatch):
    """Make the plugin see ``pyramids-core`` as absent, the state that offers a fresh install."""
    monkeypatch.setattr(deps, "pyramids_installed", lambda: False)
    monkeypatch.setattr(deps, "pyramids_outdated", lambda: False)


@pytest.fixture
def outdated_pyramids(monkeypatch):
    """Make the plugin see ``pyramids-core`` as present but too old, the upgrade state."""
    monkeypatch.setattr(deps, "pyramids_installed", lambda: True)
    monkeypatch.setattr(deps, "pyramids_outdated", lambda: True)


def test_the_offer_shows_three_buttons_and_states_what_it_needs(
    driver, clean_dismissal, installs, missing_pyramids
):
    """The dialog offers exactly Yes / Not now / Don't ask again and names what it requires."""
    driver.expect("Not now")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert driver.pending == [], "the queued dialog never appeared"
    assert driver.titles == ["Pyramids: install pyramids-core"]
    dialog = driver.seen[0]
    assert dialog["buttons"] == ["Not now", "Don't ask again", "Yes"], (
        "the order is asserted, not just the set: it is the order the user sees, and Qt assigns "
        "roles from it"
    )
    assert dialog["clicked"] == "Not now", f"clicked {dialog['clicked']!r}"
    text = str(dialog["text"])
    assert html.escape(deps.PYRAMIDS_REQUIREMENT) in text, (
        "the dialog must state the requirement; it is HTML-escaped, so '>=' arrives as '&gt;='"
    )
    assert html.escape(deps._python_executable()) in text, "and the interpreter it would use"


def test_dont_ask_again_records_the_decline(driver, clean_dismissal, installs, missing_pyramids):
    """ "Don't ask again" persists the decline for this state, and installs nothing."""
    driver.expect("Don't ask again")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert driver.seen[0]["clicked"] == "Don't ask again"
    assert QgsSettings().value(INSTALL_OFFER_DISMISSED_KEY) == "missing"
    assert installs == [], "declining must not run the installer"


def test_not_now_declines_without_recording_it(driver, clean_dismissal, installs, missing_pyramids):
    """ "Not now" installs nothing and records nothing, so the offer returns on the next start."""
    driver.expect("Not now")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert QgsSettings().value(INSTALL_OFFER_DISMISSED_KEY, "") == ""
    assert installs == []


def test_a_recorded_decline_shows_no_dialog(driver, clean_dismissal, installs, missing_pyramids):
    """With the decline already recorded for this state, the offer opens nothing at all.

    The queue is then re-armed and answered for real, which is what makes the silence meaningful:
    asserting only ``seen == []`` would pass just as well against a driver that never ran.
    """
    QgsSettings().setValue(INSTALL_OFFER_DISMISSED_KEY, "missing")
    driver.expect("Not now")
    PyramidsPlugin(None)._run_install_offer()

    assert driver.seen == [], "a dialog appeared despite the recorded decline"
    assert installs == []
    assert driver.pending == ["Not now"], "the queue should still be waiting, unanswered"

    driver.expect("Not now")
    QgsSettings().remove(INSTALL_OFFER_DISMISSED_KEY)
    PyramidsPlugin(None)._run_install_offer()

    assert driver.ticks > 0, "the poll timer never ran, so the silence above proved nothing"
    assert driver.titles == ["Pyramids: install pyramids-core"]


def test_pyramids_present_and_current_is_silent(driver, clean_dismissal, installs, monkeypatch):
    """A satisfied state offers nothing: no dialog, no install, nothing recorded.

    As with the recorded-decline test, the driver is then re-armed against a state that *does*
    offer, because "no dialog appeared" is indistinguishable from "the driver never ran".
    """
    monkeypatch.setattr(deps, "pyramids_installed", lambda: True)
    monkeypatch.setattr(deps, "pyramids_outdated", lambda: False)
    driver.expect("Not now")
    PyramidsPlugin(None)._run_install_offer()

    assert driver.seen == [], "nothing should be offered when pyramids is present and current"
    assert installs == []
    assert QgsSettings().value(INSTALL_OFFER_DISMISSED_KEY, "") == ""
    assert driver.pending == ["Not now"], "the queue should still be waiting, unanswered"

    monkeypatch.setattr(deps, "pyramids_installed", lambda: False)
    driver.expect("Not now")
    PyramidsPlugin(None)._run_install_offer()

    assert driver.ticks > 0, "the poll timer never ran, so the silence above proved nothing"
    assert driver.titles == ["Pyramids: install pyramids-core"]


def test_accepting_runs_the_installer_and_reports_success(
    driver, clean_dismissal, becomes_installed
):
    """Yes installs, the real outcome dialog confirms it, and the decline is cleared.

    The outcome dialog is the genuine one here, not a stub: it is the only path that returns
    ``True``, and so the only one that makes the caller clear the recorded decline.
    """
    QgsSettings().setValue(INSTALL_OFFER_DISMISSED_KEY, "outdated")  # the OTHER state's decline
    driver.expect("Yes", "OK")

    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert driver.pending == [], "the outcome dialog never appeared"
    assert becomes_installed == [{"upgrade": False}], f"installer calls were {becomes_installed}"
    assert "Restart QGIS" in str(driver.seen[1]["text"]), f"outcome was {driver.seen[1]['text']!r}"
    assert QgsSettings().value(INSTALL_OFFER_DISMISSED_KEY, "") == "", (
        "a successful install must clear the decline, including one recorded for the other state"
    )


def test_an_outdated_install_is_offered_as_an_upgrade(
    driver, clean_dismissal, installs, outdated_pyramids
):
    """An installed-but-old pyramids is offered as an upgrade, and recorded under its own state."""
    driver.expect("Don't ask again")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert "older than the supported version" in str(driver.seen[0]["text"])
    assert QgsSettings().value(INSTALL_OFFER_DISMISSED_KEY) == "outdated", (
        "the decline is per state, so declining an upgrade must not silence a missing install"
    )


def test_accepting_an_upgrade_passes_upgrade_true(
    driver, clean_dismissal, installs, outdated_pyramids
):
    """Accepting in the outdated state asks the installer to upgrade, not to install fresh.

    Two dialogs are queued because the real outcome dialog runs: the stubbed install reports
    success while ``pyramids_outdated`` still answers true, which is the incomplete outcome.
    """
    driver.expect("Yes", "OK")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert driver.pending == [], f"a queued dialog never appeared: {driver.pending}"
    assert installs == [{"upgrade": True}], f"installer calls were {installs}"


def test_a_failed_install_reports_the_manual_command(
    driver, clean_dismissal, missing_pyramids, monkeypatch
):
    """When the installer fails, the outcome dialog hands the user the command to run by hand."""
    monkeypatch.setattr(deps, "install_pyramids", lambda **kw: (False, "pip exploded"))
    driver.expect("Yes", "OK")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert len(driver.seen) == 2, f"expected the offer and an outcome dialog, got {driver.titles}"
    outcome = driver.seen[1]
    assert "failed" in str(outcome["title"]).lower()
    assert "pip install" in str(outcome["text"]), "the outcome must name the manual command"
    assert QgsSettings().value(INSTALL_OFFER_DISMISSED_KEY, "") == ""


def test_an_incomplete_install_names_the_interpreter_it_targeted(
    driver, clean_dismissal, missing_pyramids, monkeypatch
):
    """pip succeeding while pyramids stays unimportable is reported as incomplete, not success.

    This is the "installed into the wrong interpreter" case: the message has to name the target so
    the user can see which Python was actually used.
    """
    monkeypatch.setattr(deps, "install_pyramids", lambda **kw: (True, "Successfully installed"))
    driver.expect("Yes", "OK")

    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    outcome = driver.seen[1]
    assert "incomplete" in str(outcome["title"]).lower(), f"title was {outcome['title']!r}"
    assert "not importable" in str(outcome["text"])
    assert "pip install" in str(outcome["text"]), "the user needs the manual command"
    assert QgsSettings().value(INSTALL_OFFER_DISMISSED_KEY, "") == ""


def test_the_outcome_dialog_shows_the_tail_of_the_pip_output(
    driver, clean_dismissal, missing_pyramids, monkeypatch
):
    """A failure shows the end of pip's output, which is where its error actually is."""
    noise = "\n".join(f"line {index}" for index in range(400))
    monkeypatch.setattr(
        deps, "install_pyramids", lambda **kw: (False, f"FIRST-LINE\n{noise}\nERROR: no such wheel")
    )
    driver.expect("Yes", "OK")

    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    text = str(driver.seen[1]["text"])
    assert "ERROR: no such wheel" in text, "the tail of the output must be shown"
    assert "FIRST-LINE" not in text, "the output is truncated to its tail, so the head is dropped"


def test_the_driver_reports_a_button_it_cannot_find(
    driver, clean_dismissal, installs, missing_pyramids
):
    """A mismatched label is recorded and the dialog rejected, rather than hanging the run.

    This one takes ``installs`` like every other test: it answers the dialog in an unexpected way,
    so it is the last place that should be able to reach real ``pip``.
    """
    driver.expect("No Such Button")
    PyramidsPlugin(None)._run_install_offer()

    assert driver.errors, "a mismatched label must be reported"
    assert "No Such Button" in driver.errors[0], f"errors were {driver.errors}"
    assert len(driver.seen) == 1, "the dialog was still inspected before being rejected"
    assert driver.seen[0]["clicked"] is None, "nothing should have been clicked"
    assert installs == [], "rejecting the offer must not reach the installer"
    assert QgsSettings().value(INSTALL_OFFER_DISMISSED_KEY, "") == ""


def test_a_modal_the_active_lookup_cannot_see_is_still_answered(
    driver, monkeypatch, transient_modal
):
    """A modal that ``activeModalWidget()`` reports as absent is still found and closed.

    This is the one failure mode that cannot merely fail a test: if the driver gives up without
    closing the dialog, ``exec()`` never returns, the test body is never reached, and the CI job
    runs to its own timeout with no output at all. The top-level scan in :func:`_open_modal` is what
    prevents it, so blinding the primary lookup is the regression test for it.
    """
    monkeypatch.setattr(QApplication, "activeModalWidget", staticmethod(lambda: None))
    box = transient_modal(QMessageBox())
    box.setWindowTitle("blinded modal")
    box.setText("activeModalWidget() cannot see me")
    box.addButton(QMessageBox.StandardButton.Yes)

    driver.expect("Yes")
    box.exec()

    assert driver.titles == ["blinded modal"], "the fallback scan did not find the dialog"
    assert driver.seen[0]["clicked"] == "Yes"
    assert not box.isVisible(), "exec() only returns because the dialog was closed"


def test_a_modal_that_is_not_a_message_box_is_closed_not_crashed_into(driver, transient_modal):
    """A modal with no buttons is reported and closed, never crashed into.

    An exception inside a Qt timer slot aborts the interpreter rather than failing a test, so the
    driver has to survive a dialog that has no ``buttons()`` at all.
    """
    dialog = transient_modal(QDialog())
    dialog.setWindowTitle("not a message box")
    dialog.setModal(True)
    driver.expect("Yes")
    dialog.exec()

    assert driver.errors, "the unexpected modal should have been reported"
    assert driver.errors[0].startswith("not a message box:"), (
        f"the isinstance guard should have produced this error, got {driver.errors!r}"
    )
    assert driver.seen == [], "a dialog with no buttons must not be recorded as answered"
    assert not dialog.isVisible(), "the dialog must have closed, or exec() would never return"


def test_the_persisted_key_is_the_documented_string():
    """The settings key is a persistence contract, so its literal value is pinned here.

    Everything else refers to :data:`INSTALL_OFFER_DISMISSED_KEY`, which means a rename would keep
    the whole suite green while silently forgetting every user's recorded decline.
    """
    assert INSTALL_OFFER_DISMISSED_KEY == "pyramids/install_offer_dismissed_for"


def test_an_exception_in_the_timer_slot_is_recorded_not_fatal(driver, monkeypatch, transient_modal):
    """A failure inside the Qt slot is caught, recorded, and the modal still closed.

    An exception escaping a timer slot aborts the interpreter rather than failing a test, so this
    pins the handler that prevents it — including that the rescue still runs afterwards.
    """

    def explode(self, box, label):
        """Stand in for ``_answer`` and raise, to exercise the slot's own error handling."""
        raise RuntimeError("boom inside the slot")

    monkeypatch.setattr(DialogDriver, "_answer", explode)
    box = transient_modal(QMessageBox())
    box.setWindowTitle("exploding answer")
    box.setText("the handler will raise while answering me")
    box.addButton(QMessageBox.StandardButton.Yes)

    driver.expect("Yes")
    box.exec()

    assert any("RuntimeError in the timer slot" in error for error in driver.errors), (
        f"the slot exception was not recorded: {driver.errors!r}"
    )
    assert not box.isVisible(), "the rescue must still close the modal, or exec() would hang"


def test_a_dialog_nobody_answers_is_given_up_on_and_closed(driver, transient_modal):
    """An unexpected modal is force-closed once the queue drains, with the reason recorded.

    Nothing is queued here, so the driver has no instruction for the dialog that appears. The point
    is that it still closes it: an open modal means ``exec()`` never returns.
    """
    box = transient_modal(QMessageBox())
    box.setWindowTitle("unexpected")
    box.setText("nothing queued for me")
    box.addButton(QMessageBox.StandardButton.Yes)

    driver.expect()  # an empty queue: the driver should notice the modal and close it
    box.exec()

    assert any("still open once the queue drained" in error for error in driver.errors), (
        f"the unexpected modal was not reported: {driver.errors!r}"
    )
    assert not box.isVisible()


def test_expect_stops_a_previous_arming(driver):
    """Re-arming replaces the previous queue instead of leaving two timers polling.

    Two live timers would answer dialogs twice over and interleave queues, which is the cross-test
    cascade this driver exists to avoid.
    """
    driver.expect("Yes", "OK")
    assert driver.pending == ["Yes", "OK"]
    driver.expect("Not now")
    assert driver.pending == ["Not now"], "the previous queue should have been discarded"
    driver.stop()
    assert driver.pending == ["Not now"], "stop() must not change what was queued"


def test_accepting_restores_the_override_cursor(driver, clean_dismissal, becomes_installed):
    """The busy cursor set for the install is always restored, even though a dialog follows it.

    A leaked override cursor leaves the whole QGIS window showing a wait cursor for the rest of the
    session, which no other assertion here would notice.
    """
    driver.expect("Yes", "OK")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert QApplication.overrideCursor() is None, "the wait cursor was left applied"


def test_the_offer_is_rendered_as_rich_text(driver, clean_dismissal, installs, missing_pyramids):
    """The dialog is rich text, because its message is built as HTML.

    Rendering it as plain text would show the user literal ``<b>`` and ``<code>`` tags, which is a
    visible regression that no text assertion here would catch.
    """
    driver.expect("Not now")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    assert driver.seen[0]["format"] == Qt.TextFormat.RichText, (
        f"the offer must render as rich text, got {driver.seen[0]['format']!r}"
    )


def test_an_expected_dialog_that_never_appears_hits_the_tick_budget(driver, monkeypatch):
    """A queued dialog that never opens ends in a reported give-up, not an endless wait.

    No dialog is created at all, so the queue cannot drain and :data:`RESCUE_TICKS` is the only
    thing that stops the driver polling for the rest of the session. The budget is lowered and a
    plain event loop is run, because ticks only advance while some loop is spinning.
    """
    monkeypatch.setitem(globals(), "RESCUE_TICKS", 4)
    loop = QEventLoop()
    QTimer.singleShot(400, loop.quit)

    driver.expect("Yes")
    loop.exec()

    assert any("gave up waiting" in error for error in driver.errors), (
        f"the tick budget did not fire: {driver.errors!r}"
    )
    assert driver.pending == [], "giving up must clear the queue so nothing keeps polling"


def test_clean_dismissal_puts_back_a_value_it_found(clean_dismissal):
    """The fixture restores a pre-existing decline rather than deleting it.

    Exercised directly, because the only way a test could observe it otherwise is by inspecting the
    settings of a *different* test. ``QgsSettings`` is shared with whatever profile the suite runs
    against, so silently dropping a user's recorded decline would be a real side effect.
    """
    from tests.test_install_offer_gui import clean_dismissal as fixture

    QgsSettings().setValue(INSTALL_OFFER_DISMISSED_KEY, "outdated")
    generator = fixture.__wrapped__()
    next(generator)
    assert QgsSettings().value(INSTALL_OFFER_DISMISSED_KEY, "") == "", (
        "setup should clear the key for the duration of a test"
    )
    QgsSettings().setValue(INSTALL_OFFER_DISMISSED_KEY, "missing")
    with pytest.raises(StopIteration):
        next(generator)
    assert QgsSettings().value(INSTALL_OFFER_DISMISSED_KEY) == "outdated", (
        "teardown must put back what it found, not what the test left"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("&Yes", "Yes"),
        ("Don't ask again", "Don't ask again"),
        ("Save && Close", "Save & Close"),
        ("&&", "&"),
        ("", ""),
    ],
)
def test_plain_strips_mnemonics_but_keeps_literal_ampersands(raw, expected):
    """`_plain` removes Qt's accelerator marker while leaving an escaped ``&&`` intact.

    Args:
        raw: A button label as Qt reports it.
        expected: The label as a user sees it.

    Stripping every ``&`` would turn "Save && Close" into "Save  Close" and silently stop matching
    a button whose text contains a real ampersand.
    """
    assert _plain(raw) == expected, f"_plain({raw!r}) gave {_plain(raw)!r}"


def test_a_modal_that_refuses_to_close_is_reported(driver, transient_modal, monkeypatch):
    """A modal that cannot be closed is reported rather than waited on indefinitely.

    Nothing in Python can force such a dialog away, so the only useful behaviour is to say so: the
    alternative is an unexplained hang, which is what ``pytest-timeout`` would then have to catch.
    """

    class Stubborn(QDialog):
        """A dialog that ignores both ``reject()`` and ``close()``."""

        def reject(self) -> None:
            """Refuse to be rejected."""

        def closeEvent(self, event) -> None:  # noqa: N802  (Qt-mandated method name)
            """Refuse to be closed.

            Args:
                event: The close event, which is ignored so the dialog stays visible.
            """
            event.ignore()

    dialog = transient_modal(Stubborn())
    dialog.setModal(True)
    dialog.show()
    driver.expect()
    driver._tick()
    driver._force_close()

    assert any("refused to close" in error for error in driver.errors), (
        f"a stubborn modal was not reported: {driver.errors!r}"
    )
    monkeypatch.setattr(Stubborn, "closeEvent", lambda self, event: event.accept())
    dialog.close()


def test_a_failure_while_force_closing_is_recorded_not_raised(driver, monkeypatch):
    """An exception inside the rescue is recorded, because raising there kills the process too.

    The rescue runs from the timer slot, so it is subject to the same rule as everything else
    there: it may fail, but it may not propagate.
    """

    def explode(self) -> None:
        """Stand in for ``_force_close`` and raise."""
        raise RuntimeError("rescue exploded")

    monkeypatch.setattr(DialogDriver, "_force_close", explode)
    driver._safe_force_close()

    assert any("RuntimeError while force-closing" in error for error in driver.errors), (
        f"the rescue failure was not recorded: {driver.errors!r}"
    )


def test_the_failure_hint_names_the_interpreter_and_quotes_the_requirement(
    driver, clean_dismissal, missing_pyramids, monkeypatch
):
    """The failed-install hint invokes pip through QGIS's interpreter, with the requirement quoted.

    Test scenario:
        A bare ``pip install`` hits whatever is first on PATH, which on Windows is routinely not
        the interpreter QGIS runs - the exact confusion this dialog exists to prevent, and it sat
        directly under a sentence promising an install "into QGIS's Python". The requirement must
        also be double-quoted, or pasting into cmd.exe redirects on ``>`` and installs with no
        version floor. Both were already true of the code and asserted by nothing: reverting
        either left all 54 tests green, because the neighbouring assertion only looks for the
        substring ``pip install``.
    """
    monkeypatch.setattr(deps, "install_pyramids", lambda **kw: (False, "pip exploded"))
    driver.expect("Yes", "OK")
    PyramidsPlugin(None)._run_install_offer()

    assert not driver.errors, driver.errors
    text = str(driver.seen[1]["text"])
    assert "-m pip install" in text, (
        f"the hint must invoke pip through an interpreter, not bare: {text!r}"
    )
    assert "python" in text.lower(), f"the hint must name QGIS's interpreter: {text!r}"
    quoted = f'"{html.escape(deps.PYRAMIDS_REQUIREMENT)}"'
    assert quoted in text, (
        f"the requirement must be double-quoted so a paste keeps the version floor: {text!r}"
    )
