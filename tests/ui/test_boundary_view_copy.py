# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025-2026 Shinji NAKAGAWA
"""Tests for BoundaryViewPanel copy-table helpers."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication, QTableWidgetItem

from ui.panels.boundary_view_panel import BoundaryViewPanel


def _make_panel(qapp, rows: list[str], cols: list[str], cells: list[list[str]]) -> BoundaryViewPanel:
    panel = BoundaryViewPanel()
    t = panel._table
    t.setRowCount(len(rows))
    t.setColumnCount(len(cols))
    t.setHorizontalHeaderLabels(cols)
    t.setVerticalHeaderLabels(rows)
    for r, row_cells in enumerate(cells):
        for c, text in enumerate(row_cells):
            if text is not None:
                t.setItem(r, c, QTableWidgetItem(text))
    return panel


class TestTableData:
    def test_basic(self, qapp):
        panel = _make_panel(
            qapp,
            rows=["p", "U"],
            cols=["inlet", "outlet"],
            cells=[["fixedValue", "zeroGradient"], ["fixedValue", "inletOutlet"]],
        )
        col_hdrs, row_hdrs, rows = panel._table_data()
        assert col_hdrs == ["inlet", "outlet"]
        assert row_hdrs == ["p", "U"]
        assert rows == [["fixedValue", "zeroGradient"], ["fixedValue", "inletOutlet"]]

    def test_empty_cell_becomes_dash(self, qapp):
        panel = _make_panel(qapp, rows=["p"], cols=["inlet"], cells=[[None]])
        _, _, rows = panel._table_data()
        assert rows == [["–"]]

    def test_multiline_cell_preserved(self, qapp):
        panel = _make_panel(
            qapp, rows=["p"], cols=["inlet"], cells=[["fixedValue\nvalue  0"]]
        )
        _, _, rows = panel._table_data()
        assert rows == [["fixedValue\nvalue  0"]]


class TestCopyAsMarkdown:
    def test_header_row(self, qapp):
        panel = _make_panel(
            qapp,
            rows=["p"],
            cols=["inlet", "outlet"],
            cells=[["fixedValue", "zeroGradient"]],
        )
        panel._copy_as_markdown()
        text = QApplication.clipboard().text()
        first_line = text.splitlines()[0]
        assert "inlet" in first_line
        assert "outlet" in first_line

    def test_row_header_in_data_row(self, qapp):
        panel = _make_panel(
            qapp, rows=["p"], cols=["inlet"], cells=[["fixedValue"]]
        )
        panel._copy_as_markdown()
        text = QApplication.clipboard().text()
        assert any("p" in line and "fixedValue" in line for line in text.splitlines())

    def test_separator_row(self, qapp):
        panel = _make_panel(
            qapp, rows=["p"], cols=["inlet"], cells=[["fixedValue"]]
        )
        panel._copy_as_markdown()
        lines = QApplication.clipboard().text().splitlines()
        assert any("---" in line for line in lines)

    def test_multiline_becomes_br(self, qapp):
        panel = _make_panel(
            qapp, rows=["p"], cols=["inlet"], cells=[["fixedValue\nvalue  0"]]
        )
        panel._copy_as_markdown()
        text = QApplication.clipboard().text()
        assert "fixedValue<br>value  0" in text

    def test_dash_cell(self, qapp):
        panel = _make_panel(qapp, rows=["p"], cols=["inlet"], cells=[[None]])
        panel._copy_as_markdown()
        text = QApplication.clipboard().text()
        assert "–" in text


class TestCopyAsCsv:
    def test_header_row(self, qapp):
        panel = _make_panel(
            qapp,
            rows=["p"],
            cols=["inlet", "outlet"],
            cells=[["fixedValue", "zeroGradient"]],
        )
        panel._copy_as_csv()
        first_line = QApplication.clipboard().text().splitlines()[0]
        assert "inlet" in first_line
        assert "outlet" in first_line

    def test_data_row(self, qapp):
        panel = _make_panel(
            qapp, rows=["p"], cols=["inlet"], cells=[["fixedValue"]]
        )
        panel._copy_as_csv()
        text = QApplication.clipboard().text()
        assert "p" in text
        assert "fixedValue" in text

    def test_multiline_flattened(self, qapp):
        panel = _make_panel(
            qapp, rows=["p"], cols=["inlet"], cells=[["fixedValue\nvalue  0"]]
        )
        panel._copy_as_csv()
        text = QApplication.clipboard().text()
        assert "fixedValue; value  0" in text

    def test_no_embedded_newline(self, qapp):
        """A multi-line cell must not add records: spreadsheets split pasted text on
        line breaks before parsing quotes, so an embedded newline becomes a phantom row."""
        panel = _make_panel(
            qapp,
            rows=["p", "U"],
            cols=["inlet", "outlet"],
            cells=[
                ["fixedValue\nvalue  0", "zeroGradient"],
                ["fixedValue\nvalue  (0 0 0)\nphi  phi", "inletOutlet"],
            ],
        )
        panel._copy_as_csv()
        text = QApplication.clipboard().text()
        records = text.split("\n")[:-1]  # trailing terminator leaves an empty tail
        assert len(records) == 3  # header + 2 rows
        assert "\n" not in "".join(records)

    def test_no_carriage_return(self, qapp):
        """Records end in LF, never CRLF: a clipboard bridge translating LF on the way to
        Windows turns a CRLF terminator into "\r\r\n", a blank row between every row."""
        panel = _make_panel(
            qapp, rows=["p"], cols=["inlet"], cells=[["fixedValue\nvalue  0"]]
        )
        panel._copy_as_csv()
        assert "\r" not in QApplication.clipboard().text()

    def test_comma_in_cell_quoted(self, qapp):
        panel = _make_panel(
            qapp, rows=["p"], cols=["inlet"], cells=[["a, b"]]
        )
        panel._copy_as_csv()
        text = QApplication.clipboard().text()
        assert '"a, b"' in text

    def test_embedded_quote_doubled(self, qapp):
        panel = _make_panel(
            qapp, rows=["p"], cols=["inlet"], cells=[['type "a"']]
        )
        panel._copy_as_csv()
        text = QApplication.clipboard().text()
        assert '"type ""a"""' in text


class TestCopyAsCsvMultiline:
    """The second menu entry keeps the RFC 4180 multi-line output for importers that
    parse quoted fields (LibreOffice Calc's paste dialog does)."""

    def test_multiline_preserved(self, qapp):
        panel = _make_panel(
            qapp, rows=["p"], cols=["inlet"], cells=[["fixedValue\nvalue  0"]]
        )
        panel._copy_as_csv_multiline()
        text = QApplication.clipboard().text()
        assert '"fixedValue\nvalue  0"' in text

    def test_no_carriage_return(self, qapp):
        panel = _make_panel(
            qapp, rows=["p"], cols=["inlet"], cells=[["fixedValue\nvalue  0"]]
        )
        panel._copy_as_csv_multiline()
        assert "\r" not in QApplication.clipboard().text()

    def test_single_line_matches_flattened(self, qapp):
        panel = _make_panel(
            qapp, rows=["p"], cols=["inlet"], cells=[["fixedValue"]]
        )
        assert panel._csv_text(flatten=True) == panel._csv_text(flatten=False)
