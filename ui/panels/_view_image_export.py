# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Saving the BlockMesh 3-D view to an image file.

Split out of ui/panels/block_mesh_panel.py. Self-contained in a way the STL-overlay code
next to it is not: it needs the plotter, a parent for the dialogs, and a starting path,
and touches no panel state at all -- which is what made the move a function rather than a
controller object.

The `tr()` literals stay in this `ui/` module, where tests/ui/test_translatable_strings.py
and tests/test_i18n.py can still see them.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from i18n import tr

# Mirrors pyvista's BasePlotter.screenshot() SUPPORTED_FORMATS; anything else
# raises ValueError there, which save_view_image() turns into a warning dialog.
_IMAGE_SUFFIXES = frozenset({".png", ".jpeg", ".jpg", ".bmp", ".tif", ".tiff"})
# The Save Image dialog's one file filter, derived from the set above so the
# two cannot drift; .png leads because it is the default the panel offers.
_IMAGE_FILTER_PATTERNS = " ".join(
    "*" + s for s in [".png"] + sorted(_IMAGE_SUFFIXES - {".png"})
)


def writable_image_path(path: str) -> str:
    """*path* adjusted so plotter.screenshot() will accept its extension.

    pyvista compares the suffix against its SUPPORTED_FORMATS list *without*
    case-folding, so ".JPG" is rejected as readily as ".txt" even though the
    format itself is supported. A suffix it cannot use is therefore lowered
    when that is enough, and otherwise given a ".png" -- the alternative is
    a ValueError from inside the writer, after the user has already chosen
    where to save.
    """
    suffix = Path(path).suffix
    if suffix.lower() not in _IMAGE_SUFFIXES:
        return path + ".png"
    if suffix != suffix.lower():
        return str(Path(path).with_suffix(suffix.lower()))
    return path


def save_view_image(parent: QWidget, plotter, default_path: str) -> str | None:
    """Ask for a path and write the live 3-D view to it. Returns the path, or None.

    Capture goes through VTK's own render window rather than Qt: the plotter is a native
    child window, and QWidget.grab() returns black for it (see DEVELOPER.md's "Text drawn
    by VTK, not Qt" neighbourhood, and tools/capture_screenshots.py, which shells out to
    ImageMagick for the same reason). screenshot() with no size or background arguments
    captures the live framebuffer, which is what "as shown" means here.

    One combined image filter, deliberately, rather than one per format. The written
    format comes from the file name's extension (Pillow picks it there), while a native
    GTK chooser -- which is what Qt hands this off to on a GNOME desktop -- treats a name
    filter as a *view* filter and never rewrites the name to match it. Per-format entries
    therefore let the user pick "JPEG image", leave the name ending in .png, and get a
    PNG: a choice offered and then silently ignored. With nothing to choose there is
    nothing to contradict.

    The formats are spelled out in the filter's *name* rather than left to its
    "(*.png ...)" half, because that half never reaches the screen under GTK: Qt's gtk3
    helper builds the GTK filter's label as ``filter.left(filter.indexOf(u'('))``,
    dropping the patterns. Naming them ahead of the parenthesis is the one place both
    dialogs show.
    """
    path, _ = QFileDialog.getSaveFileName(
        parent,
        tr("Save 3-D View as Image"),
        default_path,
        f"{tr('Image files - PNG, JPEG, BMP, TIFF')} ({_IMAGE_FILTER_PATTERNS});;"
        f"{tr('All files')} (*)",
    )
    if not path:
        return None
    chosen = path
    path = writable_image_path(path)
    # The dialog checked for an existing file under the name the user gave, so a
    # corrected name has not been checked at all -- and writing it would clobber a real
    # file with no prompt of any kind.
    if path != chosen and Path(path).exists():
        answer = QMessageBox.question(
            parent,
            tr("Overwrite File?"),
            tr("{path} already exists.\nReplace it?").format(path=path),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return None
    try:
        plotter.screenshot(path)
    except Exception as exc:  # unwritable path, unsupported format, ...
        QMessageBox.warning(
            parent,
            tr("Save Image Error"),
            tr("Could not save the image:\n{error}").format(error=exc),
        )
        return None
    return path
