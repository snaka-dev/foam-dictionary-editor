# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Words for ``services/allrun_create``'s codes: row marks, skipped logs, notes.

The service returns codes because ``tests/test_i18n.py`` scans ``ui/`` only;
every code has words here (``tests/ui/test_allrun_create_ui.py``).
"""
from __future__ import annotations

from i18n import tr
from services import allrun_create as ac


def mark_label(mark: str) -> str:
    """A few words shown on the row."""
    labels = {
        ac.MARK_FAILED: tr("failed"),
        ac.MARK_INCOMPLETE: tr("did not finish"),
        ac.MARK_READ_ONLY: tr("changes nothing"),
        ac.MARK_NO_LOG: tr("suggested"),
        ac.MARK_GUESSED: tr("position guessed"),
        ac.MARK_MOVED: tr("moved"),
        ac.MARK_RESTORE: tr("added"),
        ac.MARK_PARALLEL_ONLY: tr("Allrun-parallel only"),
        ac.MARK_USER: tr("added by you"),
    }
    return labels.get(mark, mark)


def row_detail(step: ac.Proposed) -> str:
    """Where the row came from and what its marks mean, for the selected row."""
    if step.source == ac.SOURCE_LOG:
        parts = [tr("From {log}.").format(log=step.log)]
    elif step.source == ac.SOURCE_DICT:
        parts = [tr(
            "No log says this step ran; suggested because the case has {file}."
        ).format(file=step.origin)]
    else:
        parts = []
    for mark in step.marks:
        parts.append(mark_detail(mark))
    return " ".join(p for p in parts if p)


def mark_detail(mark: str) -> str:
    if mark == ac.MARK_FAILED:
        return tr(
            "Its log ends with an error, so it is unticked. Tick it if the step "
            "belongs in the run and fix the cause before running the Allrun."
        )
    if mark == ac.MARK_INCOMPLETE:
        return tr("Its log has neither End nor an error: the run was stopped or is still running.")
    if mark == ac.MARK_READ_ONLY:
        return tr(
            "This tool only reports and changes nothing a later step reads, so it "
            "is unticked. Tick it to keep the check in the script."
        )
    if mark == ac.MARK_NO_LOG:
        return ""
    if mark == ac.MARK_GUESSED:
        return tr(
            "Its place is a guess: topoSet can come before or after snappyHexMesh, "
            "depending on what its sets are for. Move it if needed."
        )
    if mark == ac.MARK_MOVED:
        return tr(
            "Its log is older than the parallel run, but in a fresh run there is "
            "nothing to reconstruct before it, so it was moved after it."
        )
    if mark == ac.MARK_PARALLEL_ONLY:
        return tr(
            "Added for Allrun-parallel, and written there only: decomposePar "
            "splits the case before the parallel run, reconstructPar puts the "
            "results back into time directories after it."
        )
    if mark == ac.MARK_USER:
        return tr(
            "Added by you. An OpenFOAM application is written with runApplication, "
            "so it writes a log; anything else is written as you typed it."
        )
    if mark == ac.MARK_RESTORE:
        return tr(
            "Added by FoDE: copies 0.orig/ to 0/ after meshing, so every run "
            "starts from the same initial fields."
        )
    return mark


def skip_text(name: str, reason: str) -> str:
    if reason == ac.SKIP_NO_HEADER:
        return tr("{log}: not an OpenFOAM application's log").format(log=name)
    if reason == ac.SKIP_EARLIER_RUN:
        return tr("{log}: an earlier run of a listed step").format(log=name)
    return name


def note_text(note: str) -> str:
    if note == ac.NOTE_FROM_DICTIONARIES:
        return tr(
            "The case has no logs, so these steps are suggested from its "
            "dictionaries. Check them and their order before creating the script."
        )
    if note == ac.NOTE_LIMITS:
        return tr(
            "Only commands that wrote a log are listed: a cp, a foamDictionary edit "
            "or a tool run without tee is not. A tool run twice appears once, and "
            "edits made between steps are not replayed."
        )
    if note == ac.NOTE_RESTORES_ZERO:
        return tr(
            "The Allrun restores 0/ from 0.orig/: make changes to initial and "
            "boundary conditions in 0.orig/, or they are lost on the next run."
        )
    if note == ac.NOTE_NO_ZERO_ORIG:
        return tr(
            "A step rewrites 0/ and the case has no 0.orig/, so running the Allrun "
            "again starts from the last run's fields. Tutorials keep a clean copy in 0.orig/."
        )
    if note == ac.NOTE_ORIG_FILES:
        return tr(
            "Foundation's cleanCase deletes every file that has a .orig copy beside it."
        )
    return note
