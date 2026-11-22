"""Tests that drive the real ``pyramids-core`` install dialog, offscreen.

The offer is the plugin's most user-visible code and was previously untestable: it opens a **modal**
``QMessageBox`` (``plugin.py``, ``box.exec()``), and ``exec()`` does not return until something
clicks a button, so a test could never reach them from its own body.

The way in is to arm the interaction *before* triggering the modal. :class:`DialogDriver` starts a
repeating ``QTimer`` which, from inside ``exec()``'s own nested event loop, finds the open dialog
and clicks a button, so ``exec()`` returns normally. That needs no extra test dependency — only the
session ``QgsApplication`` the suite already builds and the ``QT_QPA_PLATFORM=offscreen`` platform
``conftest`` already sets, so these run headless on both Qt5 and Qt6.

Four details are load-bearing, each of them learned by running it:

- The driver **polls** rather than scheduling one handler per dialog at a fixed offset. Accepting
  the offer opens a **second** modal — the outcome dialog — which does not exist until the first is
  answered, so fixed offsets race it.
- ``_run_install_offer`` imports ``install_pyramids`` from :mod:`pyramids_qgis.dependencies` *as it
  runs*, so a stub must replace the attribute on that module. Patching it on
  :mod:`pyramids_qgis.plugin` has no effect, and the real installer would run ``pip``. Every test
  here therefore takes a fixture that stubs it.
- ``QMessageBox`` has no ``buttonText()`` method, and has not since Qt 5.0, so this is not a Qt6
  difference. Buttons come from ``box.buttons()``; a standard button is matched by its
  ``QMessageBox.StandardButton`` enum rather than its text, which Qt translates, and a custom button
  by the exact text the plugin gave it.
- **Nothing may escape a Qt timer slot.** An exception there does not fail a test, it aborts the
  interpreter — observed as exit ``0xC0000409``, with no traceback and no pytest summary. Every tick
  is wrapped, and any dialog the driver cannot answer is force-closed so ``exec()`` always returns.

:attr:`DialogDriver.ticks` and :attr:`DialogDriver.pending` exist so a test can prove the driver was
alive: asserting only "no dialog appeared" would pass just as well against a driver that never ran.
"""

from __future__ import annotations

import html

import pytest
from qgis.core import QgsSettings
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QApplication, QDialog, QMessageBox

from pyramids_qgis import dependencies as deps
from pyramids_qgis.plugin import INSTALL_OFFER_DISMISSED_KEY, PyramidsPlugin

pytestmark = pytest.mark.gui

#: How many poll ticks to wait for an expected dialog before forcing it closed. Counted in ticks,
#: not wall clock: the nested ``exec()`` loop advances them, so a slow runner cannot trip it.
RESCUE_TICKS = 160

#: How often to look for an open dialog while a queue is outstanding, in milliseconds.
POLL_MS = 25

#: The standard buttons the plugin uses, keyed by the label a test asks for. Matching by enum keeps
#: these tests working under a translated Qt, where "Yes" and "OK" are localised.
STANDARD_BUTTONS = {
    "Yes": QMessageBox.StandardButton.Yes,
    "OK": QMessageBox.StandardButton.Ok,
}


def _open_modal():
    """Return the modal dialog currently on screen, or ``None``.

    ``QApplication.activeModalWidget()`` is the normal answer, but it can be ``None`` while a modal
    is genuinely open; the top-level scan is the fallback that keeps the driver — and therefore the
    whole run — from waiting forever on a dialog it cannot see.

    Returns:
        QDialog | None: The open modal dialog, preferring the active one.
    """
    active = QApplication.activeModalWidget()
    if active is not None:
        return active
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, QDialog) and widget.isVisible() and widget.isModal():
            return widget
    return None


class DialogDriver:
    """Answers a scripted queue of modal dialogs and records what it saw.

    Attributes:
        seen: One record per dialog answered, holding its ``title``, the visible ``buttons``, the
            full ``text``, the label that was ``requested`` and the ``clicked`` button's own text,
            so a lenient match cannot hide which button was really pressed.
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
                return
            if self.ticks >= RESCUE_TICKS:
                self.errors.append(f"gave up waiting for dialogs; still expecting {self._queue}")
                self._queue.clear()
                self.stop()
                self._force_close()
        except Exception as error:  # a raise here would abort the interpreter, not fail the test
            self.errors.append(f"{type(error).__name__} in the timer slot: {error}")
            self._queue.clear()
            self.stop()
            self._force_close()

    def _answer(self, box, label: str) -> None:
        """Click the button of ``box`` matching ``label``.

        Args:
            box: The modal dialog currently open. A dialog that is not a ``QMessageBox`` has no
                buttons to click, so it is recorded and closed rather than crashed into.
            label: A key of :data:`STANDARD_BUTTONS`, or the exact text of a custom button.
        """
        if not isinstance(box, QMessageBox):
            self.errors.append(f"expected a QMessageBox for {label!r}, got {type(box).__name__}")
            box.reject()
            return
        buttons = list(box.buttons())
        labels = sorted(button.text().replace("&", "") for button in buttons)
        if label in STANDARD_BUTTONS:
            wanted = STANDARD_BUTTONS[label]
            target = next((b for b in buttons if box.standardButton(b) == wanted), None)
        else:
            target = next((b for b in buttons if b.text().replace("&", "") == label), None)
        self.seen.append(
            {
                "title": box.windowTitle(),
                "buttons": labels,
                "text": box.text(),
                "requested": label,
                "clicked": target.text().replace("&", "") if target is not None else None,
            }
        )
        if target is None:
            self.errors.append(f"no button {label!r} among {labels}")
            box.reject()
            return
        target.click()

    def _force_close(self) -> None:
        """Close every open modal, so ``exec()`` returns and the test body is reached.

        Rejecting only ``activeModalWidget()`` is not enough: it is ``None`` in exactly the case the
        rescue exists for, and skipping the close leaves ``exec()`` spinning until the CI job's own
        timeout kills the run with no output at all.

        It walks ``topLevelWidgets()`` itself rather than going through :func:`_open_modal`, so the
        last resort does not depend on the same lookup that may have failed.
        """
        for _ in range(5):
            open_dialogs = [
                widget
                for widget in QApplication.topLevelWidgets()
                if isinstance(widget, QDialog) and widget.isVisible()
            ]
            if not open_dialogs:
                return
            for dialog in open_dialogs:
                dialog.reject()
                dialog.close()


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
    assert dialog["buttons"] == ["Don't ask again", "Not now", "Yes"]
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
    """A satisfied state offers nothing: no dialog, no install, nothing recorded."""
    monkeypatch.setattr(deps, "pyramids_installed", lambda: True)
    monkeypatch.setattr(deps, "pyramids_outdated", lambda: False)
    driver.expect("Not now")
    PyramidsPlugin(None)._run_install_offer()

    assert driver.seen == [], "nothing should be offered when pyramids is present and current"
    assert installs == []
    assert QgsSettings().value(INSTALL_OFFER_DISMISSED_KEY, "") == ""


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


def test_a_modal_the_active_lookup_cannot_see_is_still_answered(driver, monkeypatch):
    """A modal that ``activeModalWidget()`` reports as absent is still found and closed.

    This is the one failure mode that cannot merely fail a test: if the driver gives up without
    closing the dialog, ``exec()`` never returns, the test body is never reached, and the CI job
    runs to its own timeout with no output at all. The top-level scan in :func:`_open_modal` is what
    prevents it, so blinding the primary lookup is the regression test for it.
    """
    monkeypatch.setattr(QApplication, "activeModalWidget", staticmethod(lambda: None))
    box = QMessageBox()
    box.setWindowTitle("blinded modal")
    box.setText("activeModalWidget() cannot see me")
    box.addButton(QMessageBox.StandardButton.Yes)

    driver.expect("Yes")
    box.exec()

    assert driver.titles == ["blinded modal"], "the fallback scan did not find the dialog"
    assert driver.seen[0]["clicked"] == "Yes"
    assert not box.isVisible(), "exec() only returns because the dialog was closed"


def test_a_modal_that_is_not_a_message_box_is_closed_not_crashed_into(driver):
    """A modal with no buttons is reported and closed, never crashed into.

    An exception inside a Qt timer slot aborts the interpreter rather than failing a test, so the
    driver has to survive a dialog that has no ``buttons()`` at all.
    """
    dialog = QDialog()
    dialog.setWindowTitle("not a message box")
    dialog.setModal(True)
    driver.expect("Yes")
    dialog.exec()

    assert driver.errors, "the unexpected modal should have been reported"
    assert "QDialog" in driver.errors[0], f"errors were {driver.errors}"
    assert not dialog.isVisible(), "the dialog must have closed, or exec() would never return"
