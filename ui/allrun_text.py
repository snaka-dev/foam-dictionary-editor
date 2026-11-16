# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Words for ``services/allrun``'s codes: step states, suspicions, script notes.

The service returns codes because ``tests/test_i18n.py`` scans ``ui/`` only;
every code has words here (``tests/ui/test_allrun_ui.py``).
"""
from __future__ import annotations

from i18n import tr
from services import allrun as ar


def state_label(status: ar.StepStatus) -> str:
    if status.state == ar.DONE:
        return tr("Done (check)") if status.suspect else tr("Done")
    if status.state == ar.FAILED:
        return tr("Failed")
    if status.state == ar.RUNNING:
        return tr("Running")
    if status.state == ar.INCOMPLETE:
        return tr("Incomplete")
    if status.state == ar.NOT_RUN:
        return tr("Not run")
    return ""


def state_tooltip(step: ar.Step, status: ar.StepStatus) -> str:
    log = step.log
    if step.kind == ar.OTHER:
        return tr("Not tracked: this command leaves no log.")
    if not log:
        return tr("The application this step runs could not be told, so neither can its log.")
    if status.state == ar.NOT_RUN:
        text = tr("No {log} yet: the script will run this step.").format(log=log)
    elif status.state == ar.DONE:
        text = tr("{log} ends with End.").format(log=log)
    elif status.state == ar.FAILED:
        text = tr(
            "{log} holds an error. Double-click to see it explained in View Log Summary."
        ).format(log=log)
    elif status.state == ar.RUNNING:
        text = tr("{log} is being written: the step is running now.").format(log=log)
    elif status.watched:
        text = tr(
            "{log} has neither End nor an error, and nothing is writing it any more: "
            "the step was stopped or killed."
        ).format(log=log)
    else:
        text = tr(
            "{log} has neither End nor an error: the step is still running, or was stopped."
        ).format(log=log)
    if status.state not in (ar.NOT_RUN, ar.RUNNING) and not step.always_reruns:
        text += " " + tr("Running the Allrun again skips this step, because its log exists.")
    if step.always_reruns:
        text += " " + tr("The script always re-runs this step (-o/-a).")
    if status.suspect == ar.SUSPECT_AFTER_FAILURE:
        text += " " + tr(
            "It ran after an earlier step failed or did not finish, so its results "
            "may be wrong — run it again once that step is fixed."
        )
    elif status.suspect == ar.SUSPECT_OUTDATED:
        text += " " + tr(
            "An earlier step was run again after it, so its results may be out of "
            "date — run it again."
        )
    if step.conditional:
        text += " " + tr("It sits inside an if/for block: the script may not run it.")
    return text


def note_text(note: str) -> str:
    if note == ar.NOTE_BRANCHES:
        return tr(
            "This script has loops or conditions: the steps it holds are listed, "
            "but Run From Here is off, since its lines do not run in a straight line."
        )
    if note == ar.NOTE_SUBDIRECTORY:
        return tr("Steps the script runs in other directories are not listed.")
    if note == ar.NOTE_UNRESOLVED_APP:
        return tr("For some steps the application could not be told (a shell variable).")
    return note
