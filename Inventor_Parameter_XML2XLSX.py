# -*- coding: utf-8 -*-
"""Export Autodesk Inventor user parameters from XML files to Excel workbooks.

Created on 2026-07-23
Last updated 2026-07-23

Author
------
William W. Wallace
Primary Email: wwallace@nrao.edu
Secondary Email: naval.antennas@gmail.com
Business Phone: +1 (304) 456-2216

Purpose
-------
This application provides a small Qt (PySide6, accessed through the ``qtpy``
abstraction layer) GUI that reads Autodesk Inventor XML parameter export files,
filters the data to keep only *named* user parameters, and writes the results
to Excel workbooks that Inventor 2025 (or any spreadsheet consumer) can
reference.

Reference input schema (Inventor "ParamWithValueList" export)
-------------------------------------------------------------
The Inventor XML export used as the reference for this tool is structured as::

    <ParamWithValueList>
      <version>20080502</version>
      <parameterTypes> ... </parameterTypes>   <!-- type dictionary, ignored -->
      <parameters>
        <ParamWithValue>
          <name>QZ_offset</name>       <!-- parameter name          -> Parameter -->
          <typeCode>ft</typeCode>      <!-- unit token (in/ft/ul)   -> Units     -->
          <value>7.5 ft</value>        <!-- value or expression     -> Value     -->
          <comment />                  <!-- optional comment         -> Comment   -->
          <isKey>false</isKey>         <!-- ignored -->
          <tolerance>...</tolerance>   <!-- ignored (present on model dims) -->
        </ParamWithValue>
        ...
      </parameters>
    </ParamWithValueList>

The important structural facts driving the parser are:
    * Each parameter is a ``<ParamWithValue>`` element, NOT ``<Parameter>``.
    * The fields are *child elements*, not XML attributes.
    * The unit token lives in the ``<typeCode>`` child (e.g. ``in``, ``ft``,
      ``ul`` where ``ul`` means "unitless").

Notes
-----
- Inventor-generated model dimensions such as ``d1``, ``d25``, and ``d103`` are
  excluded; only meaningfully named user parameters (``Chamber_len``,
  ``QZ_offset``, ``Abz_num_wd`` ...) are kept.
- The GUI supports previewing the first selected XML file before conversion.
- The application safely reuses an existing QApplication instance when run
  from interactive environments such as Spyder, IPython, or Jupyter.
- A View menu provides a Light/Dark display toggle.

Compatibility
-------------
Written to run identically on CPython 3.8 through 3.12.
``from __future__ import annotations`` (PEP 563) is used so that PEP 585
generic hints such as ``list[dict]`` are treated as strings and therefore do
NOT raise ``TypeError`` under Python 3.8, where ``list[...]`` subscripting was
not yet available at runtime.

Revision History
----------------
Semantic scheme: External Release . Internal Release . Working version
(0.0.1 is the first internal draft).

0.0.1
    Initial GUI utility for converting Inventor XML parameter exports to Excel.
0.0.2
    Added filtering for user parameters only and safe QApplication reuse.
0.0.3  (2026-07-23)
    * FIX (critical): the parser matched the tag ``parameter`` while the
      reference Inventor export uses ``ParamWithValue`` with child elements.
      The old code therefore returned zero rows for every real file. The parser
      now recognises ``ParamWithValue`` (and still tolerates a generic
      ``Parameter`` layout) and reads the ``name`` / ``value`` / ``typeCode`` /
      ``comment`` child elements, mapping ``typeCode`` to the Units column.
    * FIX (compat): added ``from __future__ import annotations`` so ``list[...]``
      type hints do not crash on Python 3.8.
    * CHANGE: switched Qt imports to the ``qtpy`` abstraction layer
      (backend pinned to PySide6) per project convention.
    * CHANGE: fully scoped Qt enums (``Qt.ItemFlag.ItemIsEditable`` etc.) to
      avoid PySide6 6.x deprecation warnings.
    * NEW: View menu with Light/Dark display toggle.
    * NEW: bold header row in the exported workbook.
"""

# NOTE: ``from __future__ import annotations`` MUST be the first statement after
# the module docstring. It defers evaluation of all annotations (PEP 563),
# which is what makes ``list[dict]`` / ``list[Path]`` hints safe on Python 3.8.
from __future__ import annotations

import os
import sys
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Qt backend selection.
# Per project convention we program against the ``qtpy`` abstraction layer and
# pin the concrete binding to PySide6. ``setdefault`` means an externally set
# QT_API (e.g. in a Spyder session) is respected rather than overridden.
# ---------------------------------------------------------------------------
os.environ.setdefault("QT_API", "pyside6")

from qtpy.QtCore import Qt                     # noqa: E402  (import after QT_API set)
from qtpy.QtGui import QAction                 # noqa: E402  (QAction lives in QtGui on Qt6)
from qtpy.QtWidgets import (                    # noqa: E402
    QApplication,
    QAbstractItemView,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Module version string, kept in sync with the Revision History docstring.
__version__ = "0.0.3"

# Column ordering for both the GUI preview and the Excel export.
COLUMNS = ["Parameter", "Value", "Units", "Comment"]

# XML tag local-names (lower-cased) that represent a single parameter record.
# The reference Inventor export uses ``ParamWithValue``; ``parameter`` is kept
# as a tolerant fallback for other/legacy export layouts.
PARAMETER_TAGS = ("paramwithvalue", "parameter")

# Keep a module-level reference to the main window so the GUI is not garbage-
# collected immediately when launched from interactive environments such as
# Spyder, IPython, or Jupyter.
WINDOW_INSTANCE = None

# Minimal dark-mode stylesheet. Light mode simply clears the stylesheet and
# falls back to the platform default palette.
DARK_STYLESHEET = """
QWidget { background-color: #2b2b2b; color: #e6e6e6; }
QLineEdit, QPlainTextEdit, QTableWidget {
    background-color: #3c3f41; color: #e6e6e6; border: 1px solid #555;
}
QTableWidget { gridline-color: #555; }
QHeaderView::section { background-color: #45494b; color: #e6e6e6; padding: 4px; }
QPushButton {
    background-color: #3c3f41; color: #e6e6e6;
    border: 1px solid #666; padding: 4px 10px; border-radius: 3px;
}
QPushButton:hover { background-color: #4a4e50; }
QPushButton:pressed { background-color: #555a5c; }
QMenuBar, QMenu { background-color: #2b2b2b; color: #e6e6e6; }
QMenuBar::item:selected, QMenu::item:selected { background-color: #4a4e50; }
"""


# ===========================================================================
# XML parsing helpers (pure functions -- no Qt dependency, easy to unit test)
# ===========================================================================
def local_name(tag: str) -> str:
    """Strip an XML namespace prefix and return only the local tag name.

    Inventor XML may use namespace-qualified tags such as
    ``{some_namespace}ParamWithValue``. This reduces that to ``ParamWithValue``.

    Parameters
    ----------
    tag : str
        The raw ``element.tag`` string from ElementTree.

    Returns
    -------
    str
        The local tag name with any ``{namespace}`` prefix removed.
    """
    # ElementTree encodes namespaces as "{uri}localname"; split on the closing
    # brace and take the trailing local part when a namespace is present.
    return tag.split('}')[-1] if '}' in tag else tag


def text_or_blank(elem) -> str:
    """Return stripped element text, or an empty string when there is none.

    Parameters
    ----------
    elem : xml.etree.ElementTree.Element or None
        The element whose text is wanted. ``None`` is accepted so callers can
        pass the result of a possibly-missing ``find`` directly.

    Returns
    -------
    str
        ``elem.text`` stripped of surrounding whitespace, or ``''``.
    """
    # Guard against both a missing element and an empty self-closing tag such as
    # ``<comment />`` whose ``.text`` attribute is ``None``.
    return elem.text.strip() if elem is not None and elem.text else ''


def looks_like_model_dimension(name: str) -> bool:
    """Identify Inventor auto-generated model dimensions such as d1, d25, d103.

    Autodesk creates model parameters automatically and assigns default names of
    the form ``d<number>`` (d0, d1, d2, ...). User parameters, by contrast, are
    created explicitly and carry meaningful names. This predicate is the basis
    of the "user parameters only" filter.

    Parameters
    ----------
    name : str
        Parameter name extracted from the XML.

    Returns
    -------
    bool
        True if ``name`` matches the ``d<number>`` auto-generated pattern.
    """
    if not name:
        return False
    lowered = name.strip().lower()
    # A model dimension is the single letter 'd' immediately followed by one or
    # more digits (e.g. "d17"). ``str.isdigit`` on the remainder rejects names
    # like "diameter" or "d_offset" because their tails are not all digits.
    return lowered.startswith('d') and lowered[1:].isdigit()


def _field_from_children(param_elem, name, value, units, comment):
    """Fill any still-blank fields from a parameter's child elements.

    Helper for :func:`parse_inventor_user_parameters`. It inspects each direct
    child of ``param_elem`` and, only when the corresponding field is still
    empty, copies the child's text into it. This keeps attribute-based layouts
    working while adding support for the child-element layout used by the
    reference ``ParamWithValue`` export.

    Parameters
    ----------
    param_elem : xml.etree.ElementTree.Element
        The parameter element whose children are scanned.
    name, value, units, comment : str
        The values gathered so far (possibly empty).

    Returns
    -------
    tuple[str, str, str, str]
        The (name, value, units, comment) tuple after child-element fill-in.
    """
    for child in param_elem:
        child_name = local_name(child.tag).lower()
        if not name and child_name == 'name':
            name = text_or_blank(child)
        elif not value and child_name in ('value', 'expression', 'equation'):
            # ``value`` holds either a literal ("7.5 ft") or an expression
            # ("Chamber_wd / 2 ul"); both are preserved verbatim.
            value = text_or_blank(child)
        elif not units and child_name in ('typecode', 'units', 'unit'):
            # In the reference export the unit token lives in <typeCode>
            # (in / ft / ul). "ul" denotes an unitless quantity.
            units = text_or_blank(child)
        elif not comment and child_name == 'comment':
            comment = text_or_blank(child)
    return name, value, units, comment


def parameter_is_user_parameter(param_elem) -> bool:
    """Return True when a parameter element is a user (not model) parameter.

    Filtering rule:
        * Exclude Inventor auto-generated model dimensions named ``d<number>``.
        * Keep meaningfully named parameters (Chamber_len, QZ_offset, ...).

    The parameter name is read from an attribute first (for attribute-style
    layouts) and, failing that, from a ``<name>`` child element (the layout of
    the reference ``ParamWithValue`` export).

    Parameters
    ----------
    param_elem : xml.etree.ElementTree.Element
        A candidate parameter element.

    Returns
    -------
    bool
        True if the element should be exported as a user parameter.
    """
    # Try attributes first (case-insensitive), then fall back to a <name> child.
    name = param_elem.attrib.get('Name') or param_elem.attrib.get('name') or ''
    if not name:
        for child in param_elem:
            if local_name(child.tag).lower() == 'name':
                name = text_or_blank(child)
                break
    return bool(name) and not looks_like_model_dimension(name)


def parse_inventor_user_parameters(xml_path: Path) -> list[dict]:
    """Parse one Inventor XML export and return its user parameters.

    The parser is deliberately tolerant of layout variations: for every field it
    checks XML attributes first and then child elements. This means it handles
    both the reference ``<ParamWithValue>`` child-element layout and any
    attribute-based ``<Parameter .../>`` layout without changes.

    Only non-``d<number>`` parameters are returned.

    Parameters
    ----------
    xml_path : Path
        Path to the input XML file.

    Returns
    -------
    list[dict]
        One dict per user parameter, keyed by the entries in :data:`COLUMNS`
        ("Parameter", "Value", "Units", "Comment"), in document order.
    """
    # Parse the whole document into an in-memory tree. ElementTree raises
    # xml.etree.ElementTree.ParseError on malformed XML, which the GUI catches.
    tree = ET.parse(xml_path)
    root = tree.getroot()

    rows: list[dict] = []

    # ``root.iter()`` walks the entire tree depth-first, so this works no matter
    # how deeply the <parameters> container is nested. We keep only elements
    # whose local tag name identifies a parameter record.
    for elem in root.iter():
        if local_name(elem.tag).lower() not in PARAMETER_TAGS:
            continue
        # Skip Inventor auto-generated model dimensions (d1, d2, ...).
        if not parameter_is_user_parameter(elem):
            continue

        # Gather fields from attributes first (tolerant of attribute layouts).
        name = elem.attrib.get('Name') or elem.attrib.get('name') or ''
        units = elem.attrib.get('Units') or elem.attrib.get('units') or ''
        comment = elem.attrib.get(
            'Comment') or elem.attrib.get('comment') or ''
        value = (
            elem.attrib.get('Expression')
            or elem.attrib.get('expression')
            or elem.attrib.get('Value')
            or elem.attrib.get('value')
            or ''
        )

        # Fill any still-blank fields from child elements (reference layout).
        name, value, units, comment = _field_from_children(
            elem, name, value, units, comment
        )

        # A record is only emitted when it has a usable name.
        if name:
            rows.append({
                'Parameter': name,
                'Value': value,
                'Units': units,
                'Comment': comment,
            })

    return rows


def write_excel(rows: list[dict], out_path: Path,
                sheet_name: str = 'UserParameters') -> None:
    """Write parsed user-parameter rows to an Excel workbook.

    Formatting choices are intentionally simple and practical:
        * a bold header row,
        * fixed, readable column widths,
        * a frozen top row so headers stay visible while scrolling,
        * no pandas index column.

    Parameters
    ----------
    rows : list[dict]
        Parsed rows as produced by :func:`parse_inventor_user_parameters`.
    out_path : Path
        Destination ``.xlsx`` path. Parent directories are created as needed.
    sheet_name : str, optional
        Worksheet name (default ``"UserParameters"``).
    """
    # Build a DataFrame with an explicit column order. Passing ``columns`` also
    # yields correctly-headed empty output if ``rows`` happens to be empty.
    df = pd.DataFrame(rows, columns=COLUMNS)

    # Ensure the target directory exists before the writer opens the file.
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # openpyxl is used explicitly so we can post-process cell formatting.
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        # Reach into the underlying openpyxl workbook/worksheet for styling.
        worksheet = writer.book[sheet_name]

        # Bold the header row (row 1). ``openpyxl.styles.Font`` is imported
        # locally to keep the module's top-level import list focused on the
        # public API used elsewhere.
        from openpyxl.styles import Font
        for cell in worksheet[1]:
            cell.font = Font(bold=True)

        # Apply fixed, human-friendly column widths (A..D map to COLUMNS).
        widths = {'A': 28, 'B': 24, 'C': 12, 'D': 36}
        for col, width in widths.items():
            worksheet.column_dimensions[col].width = width

        # Freeze the header row so it stays on-screen while scrolling.
        worksheet.freeze_panes = 'A2'


# ===========================================================================
# GUI
# ===========================================================================
class MainWindow(QMainWindow):
    """PySide6 GUI for exporting Inventor user parameters from XML to Excel.

    Main workflow:
        1. Select one or more XML files.
        2. Preview the first file's user parameters.
        3. Choose an output folder.
        4. Batch-convert all selected files to Excel.
    """

    def __init__(self):
        """Initialise window state and build the UI."""
        super().__init__()
        self.setWindowTitle(
            'Inventor User Parameters XML to Excel Converter '
            f'(v{__version__})'
        )
        self.resize(980, 640)

        # Store selected input file paths as pathlib.Path objects.
        self.selected_files: list[Path] = []

        # Keep the currently previewed rows for debugging or future expansion.
        self.preview_rows: list[dict] = []

        # Remember the active theme so the menu can show a sensible state.
        self.current_theme: str = 'light'

        # Build menus first, then the central widgets.
        self._build_menu()
        self._build_ui()

    # -- construction helpers -------------------------------------------------
    def _build_menu(self) -> None:
        """Create the menu bar, including the Light/Dark View menu."""
        menubar = self.menuBar()

        # File menu: a simple Exit action.
        file_menu = menubar.addMenu('&File')
        exit_action = QAction('E&xit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu: Light / Dark display toggle (project convention).
        view_menu = menubar.addMenu('&View')

        light_action = QAction('&Light', self)
        # ``lambda`` defers the call and pins the theme name argument.
        light_action.triggered.connect(lambda: self.apply_theme('light'))
        view_menu.addAction(light_action)

        dark_action = QAction('&Dark', self)
        dark_action.triggered.connect(lambda: self.apply_theme('dark'))
        view_menu.addAction(dark_action)

    def _build_ui(self) -> None:
        """Create and arrange all GUI widgets.

        Layout sections (top to bottom): input file selection row, output
        folder row, action buttons, preview table, and a log panel.
        """
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # -- File selection controls -----------------------------------------
        top_row = QHBoxLayout()
        self.file_label = QLabel('No XML files selected')
        self.file_label.setWordWrap(True)
        btn_add = QPushButton('Add XML Files')
        btn_add.clicked.connect(self.select_files)
        btn_clear = QPushButton('Clear')
        btn_clear.clicked.connect(self.clear_files)
        top_row.addWidget(btn_add)
        top_row.addWidget(btn_clear)
        top_row.addWidget(self.file_label, 1)
        layout.addLayout(top_row)

        # -- Output directory controls ---------------------------------------
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel('Output folder:'))
        self.output_dir = QLineEdit(str(Path.cwd()))
        btn_out = QPushButton('Browse')
        btn_out.clicked.connect(self.select_output_dir)
        out_row.addWidget(self.output_dir, 1)
        out_row.addWidget(btn_out)
        layout.addLayout(out_row)

        # -- Action buttons ---------------------------------------------------
        action_row = QHBoxLayout()
        btn_preview = QPushButton('Preview First File')
        btn_preview.clicked.connect(self.preview_first_file)
        btn_convert = QPushButton('Convert Selected Files')
        btn_convert.clicked.connect(self.convert_files)
        action_row.addWidget(btn_preview)
        action_row.addWidget(btn_convert)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        # -- Preview table ----------------------------------------------------
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        # Fully scoped Qt6 enums (avoids PySide6 6.x deprecation warnings).
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        # -- Logging area -----------------------------------------------------
        layout.addWidget(QLabel('Log:'))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 0)

    # -- theme handling -------------------------------------------------------
    def apply_theme(self, theme: str) -> None:
        """Apply the requested display theme to the whole application.

        Parameters
        ----------
        theme : str
            Either ``"light"`` (platform default palette) or ``"dark"``.
        """
        app = QApplication.instance()
        if app is None:
            # Should not happen while the GUI is running, but guard anyway.
            return
        # Setting the application-wide stylesheet cascades to every widget.
        app.setStyleSheet(DARK_STYLESHEET if theme == 'dark' else '')
        self.current_theme = theme
        self.append_log(f'Theme set to {theme}.')

    # -- logging --------------------------------------------------------------
    def append_log(self, message: str) -> None:
        """Append a single message line to the on-screen log panel."""
        self.log.appendPlainText(message)

    # -- file selection slots -------------------------------------------------
    def select_files(self) -> None:
        """Open a multi-file dialog to choose one or more XML files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            'Select XML files',
            str(Path.cwd()),
            'XML Files (*.xml);;All Files (*.*)'
        )
        if files:
            # Convert every selected path string to a Path for consistent use.
            self.selected_files = [Path(f) for f in files]
            self.file_label.setText(f'{len(files)} file(s) selected')
            self.append_log('Selected files:')
            for file_path in self.selected_files:
                self.append_log(f'  {file_path}')

    def clear_files(self) -> None:
        """Clear the file list, preview table, and log panel."""
        self.selected_files = []
        self.preview_rows = []
        self.file_label.setText('No XML files selected')
        self.table.setRowCount(0)
        self.log.clear()

    def select_output_dir(self) -> None:
        """Choose the destination folder for generated Excel files."""
        folder = QFileDialog.getExistingDirectory(
            self,
            'Select output folder',
            self.output_dir.text()
        )
        if folder:
            self.output_dir.setText(folder)

    # -- preview / conversion slots ------------------------------------------
    def preview_first_file(self) -> None:
        """Parse the first selected XML file and show it in the preview table."""
        if not self.selected_files:
            QMessageBox.warning(self, 'No files',
                                'Select one or more XML files first.')
            return
        try:
            rows = parse_inventor_user_parameters(self.selected_files[0])
            self.preview_rows = rows
            self.populate_table(rows)
            self.append_log(
                f'Previewed {len(rows)} user parameter row(s) from '
                f'{self.selected_files[0].name}'
            )
            if not rows:
                self.append_log('No user parameters found in the first file.')
        except Exception as exc:
            # Surface parse errors both in the log and via a dialog.
            self.append_log(f'Preview failed: {exc}')
            self.append_log(traceback.format_exc())
            QMessageBox.critical(self, 'Preview failed', str(exc))

    def populate_table(self, rows: list[dict]) -> None:
        """Load parsed rows into the read-only preview table widget."""
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, col_name in enumerate(COLUMNS):
                item = QTableWidgetItem(str(row.get(col_name, '')))
                # Clear the editable flag so preview cells cannot be edited.
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row_index, col_index, item)

    def convert_files(self) -> None:
        """Convert every selected XML file into a filtered Excel workbook.

        Each workbook is named after its source file with the suffix
        ``_user_parameters.xlsx`` and written to the chosen output folder.
        """
        if not self.selected_files:
            QMessageBox.warning(self, 'No files',
                                'Select one or more XML files first.')
            return

        output_dir = Path(self.output_dir.text()).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)

        ok_count = 0
        fail_count = 0
        # Process each file independently so one bad file does not abort the run.
        for xml_file in self.selected_files:
            try:
                rows = parse_inventor_user_parameters(xml_file)
                if not rows:
                    self.append_log(
                        f'Skipped {xml_file.name}: no user parameters found.'
                    )
                    fail_count += 1
                    continue
                out_file = output_dir / f'{xml_file.stem}_user_parameters.xlsx'
                write_excel(rows, out_file)
                self.append_log(
                    f'Wrote {len(rows)} user parameter row(s) to {out_file}'
                )
                ok_count += 1
            except Exception as exc:
                fail_count += 1
                self.append_log(f'Failed {xml_file.name}: {exc}')
                self.append_log(traceback.format_exc())

        QMessageBox.information(
            self,
            'Conversion complete',
            f'Successful: {ok_count}\n'
            f'Failed/skipped: {fail_count}\n'
            f'Output folder: {output_dir}'
        )


def main():
    """Qt application entry point.

    Safe for both normal execution and interactive environments (Spyder,
    IPython, Jupyter) where a QApplication may already exist:

        * reuse an existing QApplication if one is present,
        * create one only when necessary,
        * keep a global window reference alive in interactive sessions,
        * only call ``app.exec()`` when this function created the QApplication.
    """
    global WINDOW_INSTANCE
    app = QApplication.instance()
    created_app = app is None
    if created_app:
        app = QApplication(sys.argv)

    WINDOW_INSTANCE = MainWindow()
    WINDOW_INSTANCE.show()
    WINDOW_INSTANCE.raise_()
    WINDOW_INSTANCE.activateWindow()

    if created_app:
        # We own the event loop only if we created the application object.
        sys.exit(app.exec())
    # In an interactive session return the window so the caller keeps a handle.
    return WINDOW_INSTANCE


if __name__ == '__main__':
    main()
