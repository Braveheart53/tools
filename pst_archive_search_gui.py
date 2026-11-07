# -*- coding: utf-8 -*-
"""
=============================================================================
# %% Header Info...
    Title: PST Archive Search and Viewer
    Author / Requested for: W Wallace
    Contact: Not supplied
    Version: 1.0.0
    Date: 2026-10-29
    Python: 3.12
    Purpose: Read-only searching and plain-text viewing of Outlook PST archives.
    More Info:
        GUI: PySide6; PST parser: libpff-python (import name: pypff).
        RTF conversion: striprtf. No Outlook automation or network access.
        Run in an external terminal or a clean PySide6-compatible console.
# %%%%% Variable Descriptions
    archive_paths: Selected PST file paths; never opened for writing.
    search_options: Immutable-in-practice snapshot of the GUI search filters.
    archive_file: Worker-owned pypff file object; never shared with the GUI.
    folder_stack: Iterative traversal stack of (folder, logical path) pairs.
    message_record: Ordinary Python dictionary transferred to the GUI.
    result_model: GUI-owned table model; stores each record in Qt.UserRole.
    search_thread: Background reader; cancellation is cooperative.
# %%%%% More Info
    Searches rescan archives; there is no persistent email-content database.
    Sender/recipient addresses come from transport headers when available.
    Attachment contents, deleted-item recovery, and encrypted mail are excluded.
    A result cap limits row count, not bytes; large bodies can still use RAM.
=============================================================================
"""

# %% Imports and application constants
import csv
import sys
from datetime import datetime, timezone
from email import policy
from email.parser import Parser
from html.parser import HTMLParser
from pathlib import Path

# Fail clearly rather than attempting package installation from inside the GUI.
try:
    import pypff
    from striprtf.striprtf import rtf_to_text
    from PySide6.QtCore import QDate, QSettings, Qt, QThread, Signal, Slot
    from PySide6.QtGui import QAction, QStandardItem, QStandardItemModel
    from PySide6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QDateEdit, QFileDialog,
        QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
        QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
        QSpinBox, QSplitter, QTableView, QVBoxLayout, QWidget,
        QAbstractItemView,
    )
except ImportError as import_error:
    raise SystemExit(
        'Missing dependency. In this Python environment run:\n'
        'python -m pip install PySide6 libpff-python==20260926 striprtf\n'
        f'Original error: {import_error}'
    ) from import_error

APPLICATION_TITLE = 'PST Archive Search and Viewer'
APPLICATION_VERSION = '1.0.0'
RESULT_COLUMNS = ['Date (UTC)', 'Sender', 'To / Cc', 'Subject', 'Folder', 'Archive']
RECORD_KEYS = ['date', 'sender', 'recipients', 'subject', 'folder', 'archive']


# %% Text conversion helpers
class MailHTMLParser(HTMLParser):
    """Extract visible HTML text without rendering or fetching any resources."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text_fragments = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attributes):
        if tag in ('script', 'style'):
            self.hidden_depth += 1
        if not self.hidden_depth and tag in ('br', 'p', 'div', 'tr', 'li'):
            self.text_fragments.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.hidden_depth:
            self.hidden_depth -= 1
        if not self.hidden_depth and tag in ('p', 'div', 'tr', 'li'):
            self.text_fragments.append('\n')

    def handle_data(self, data):
        if not self.hidden_depth:
            self.text_fragments.append(data)


def decode_text(value, charset=None):
    """Prefer a declared charset, then UTF-8, then a lossy legacy fallback."""
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    for encoding in filter(None, (charset, 'utf-8')):
        try:
            return value.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            pass
    return value.decode('cp1252', errors='replace')


def utc_datetime(value):
    """Normalize pypff's naive UTC datetimes, or aware datetimes, to UTC."""
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


# %% Background archive reader
class ArchiveSearchThread(QThread):
    """Own all native PST handles here; emit only detached Python data."""

    records_ready = Signal(list)
    status_ready = Signal(str)
    report_ready = Signal(str)

    def __init__(self, archive_paths, search_options, parent=None):
        super().__init__(parent)
        self.archive_paths = tuple(archive_paths)
        self.search_options = dict(search_options)
        self.warning_count = 0
        self.warning_samples = []
        self.scanned_count = 0
        self.match_count = 0
        self.pending_records = []
        self.limit_reached = False

    def warn(self, context, error):
        """Count every problem but retain only 30 examples to bound log growth."""
        self.warning_count += 1
        if len(self.warning_samples) < 30:
            self.warning_samples.append(f'{context}: {error}')

    def read_property(self, native_object, property_name, default=None):
        """Missing optional properties are normal; native read failures are not."""
        try:
            return getattr(native_object, property_name, default)
        except Exception as error:
            self.warn(property_name, error)
            return default

    def extract_record(self, native_message, folder_path, archive_path):
        """Copy metadata and one preferred body representation out of libpff."""
        header_text = decode_text(self.read_property(native_message, 'transport_headers'))
        parsed_headers = Parser(policy=policy.default).parsestr(header_text)
        charset = parsed_headers.get_content_charset()
        sender = str(parsed_headers.get('From', '')) or decode_text(
            self.read_property(native_message, 'sender_name'))
        recipients = '; '.join(str(value) for field in ('To', 'Cc', 'Bcc')
                               for value in parsed_headers.get_all(field, []))
        subject = decode_text(self.read_property(native_message, 'subject'))
        message_date = utc_datetime(self.read_property(native_message, 'delivery_time'))
        if message_date is None:
            message_date = utc_datetime(
                self.read_property(native_message, 'client_submit_time'))

        # Plain text is preferred; HTML is converted without loading images.
        body_text = decode_text(self.read_property(native_message, 'plain_text_body'), charset)
        if not body_text:
            html_body = self.read_property(native_message, 'html_body')
            if html_body:
                html_parser = MailHTMLParser()
                html_parser.feed(decode_text(html_body, charset))
                html_parser.close()
                body_text = ''.join(html_parser.text_fragments)
            else:
                rtf_body = self.read_property(native_message, 'rtf_body')
                if rtf_body:
                    # Latin-1 preserves RTF byte values for striprtf to interpret.
                    rtf_source = (rtf_body.decode('latin-1')
                                  if isinstance(rtf_body, bytes) else rtf_body)
                    try:
                        body_text = rtf_to_text(rtf_source, errors='replace')
                    except Exception as error:
                        self.warn('RTF conversion', error)
        return dict(date=message_date.isoformat(sep=' ') if message_date else '',
                    sender=sender, recipients=recipients, subject=subject,
                    folder=folder_path, archive=str(archive_path), body=body_text,
                    headers=header_text, calendar_date=message_date.date() if message_date else None)

    def matches(self, message_record):
        options = self.search_options
        if options['folder'].casefold() not in message_record['folder'].casefold():
            return False
        if options['date_enabled']:
            calendar_date = message_record['calendar_date']
            if calendar_date is None or not options['start'] <= calendar_date <= options['end']:
                return False
        field_names = (['subject', 'sender', 'recipients', 'body']
                       if options['field'] == 'All text' else [options['field']])
        searchable_text = '\n'.join(message_record[field] for field in field_names).casefold()
        query = options['query'].casefold()
        # Whitespace tokens are literal substrings, not Outlook query syntax.
        return (query in searchable_text if options['phrase'] else
                all(word in searchable_text for word in query.split()))

    def scan_archive(self, archive_path):
        archive_file = pypff.file()
        try:
            archive_file.open(str(archive_path), 'r')
            root_folder = archive_file.get_root_folder()
            if root_folder is None:
                raise RuntimeError('Archive contains no readable root folder.')
            folder_stack = [(root_folder, '/')]
            while folder_stack and not self.isInterruptionRequested() and not self.limit_reached:
                folder, folder_path = folder_stack.pop()
                message_count = self.read_property(folder, 'number_of_sub_messages', 0) or 0
                for message_index in range(message_count):
                    if self.isInterruptionRequested() or self.limit_reached:
                        break
                    self.scanned_count += 1
                    try:
                        native_message = folder.get_sub_message(message_index)
                        message_record = self.extract_record(native_message, folder_path, archive_path)
                        if self.matches(message_record):
                            self.pending_records.append(message_record)
                            self.match_count += 1
                            self.limit_reached = self.match_count >= self.search_options['limit']
                            if len(self.pending_records) >= 25:
                                self.flush_records()
                    except Exception as error:
                        self.warn(f'{archive_path.name}:{folder_path} item {message_index}', error)
                    if self.scanned_count % 100 == 0:
                        self.status_ready.emit(
                            f'Scanned {self.scanned_count:,}; matched {self.match_count:,}; '
                            f'warnings {self.warning_count:,}')
                child_count = self.read_property(folder, 'number_of_sub_folders', 0) or 0
                for child_index in reversed(range(child_count)):
                    if self.isInterruptionRequested() or self.limit_reached:
                        break
                    try:
                        child_folder = folder.get_sub_folder(child_index)
                        child_name = decode_text(self.read_property(child_folder, 'name')) or '(unnamed)'
                        folder_stack.append((child_folder, folder_path.rstrip('/') + '/' + child_name))
                    except Exception as error:
                        self.warn(f'Subfolder {child_index}', error)
        finally:
            # Close in the same thread even after cancellation or parse errors.
            try:
                archive_file.close()
            except Exception as error:
                self.warn(f'Closing {archive_path.name}', error)

    def flush_records(self):
        if self.pending_records:
            self.records_ready.emit(self.pending_records)
            self.pending_records = []

    def run(self):
        for archive_path in self.archive_paths:
            if self.isInterruptionRequested() or self.limit_reached:
                break
            self.status_ready.emit(f'Reading {archive_path.name} ...')
            try:
                self.scan_archive(archive_path)
            except Exception as error:
                self.warn(str(archive_path), error)
        self.flush_records()
        outcome = ('Cancelled; partial results' if self.isInterruptionRequested() else
                   'Result limit reached; search incomplete' if self.limit_reached else
                   'Traversal finished')
        self.report_ready.emit(
            f'{outcome}. Scanned {self.scanned_count:,}; matched {self.match_count:,}; '
            f'warnings {self.warning_count:,}.\n'
            'Warnings can mean missing messages, fields, or folders.\n' +
            '\n'.join(self.warning_samples))


# %% Main window and GUI layout
class PSTSearchWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.archive_paths = []
        self.search_thread = None
        self.settings = QSettings('WWallace', 'PSTArchiveSearch')
        self.setWindowTitle(f'{APPLICATION_TITLE} — {APPLICATION_VERSION}')
        self.resize(1250, 850)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        self.archive_label = QLabel('No PST archives selected.')
        self.archive_label.setWordWrap(True)
        main_layout.addWidget(self.archive_label)

        # Keep filter controls together so they can be frozen during a scan.
        self.filter_panel = QWidget()
        filter_layout = QFormLayout(self.filter_panel)
        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText('Blank = list messages; otherwise literal words or phrase')
        self.field_combo = QComboBox()
        self.field_combo.addItems(['All text', 'subject', 'sender', 'recipients', 'body'])
        self.phrase_check = QCheckBox('Match the entire query as one phrase')
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText('Optional folder-path substring')
        self.date_check = QCheckBox('Use inclusive UTC date range')
        self.start_date = QDateEdit(QDate.currentDate().addYears(-1))
        self.end_date = QDateEdit(QDate.currentDate())
        date_layout = QHBoxLayout()
        for date_edit in (self.start_date, self.end_date):
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat('yyyy-MM-dd')
        date_layout.addWidget(self.date_check)
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(self.end_date)
        self.result_limit = QSpinBox()
        self.result_limit.setRange(1, 100000)
        self.result_limit.setValue(2000)
        filter_layout.addRow('Search:', self.query_edit)
        filter_layout.addRow('Field:', self.field_combo)
        filter_layout.addRow('', self.phrase_check)
        filter_layout.addRow('Folder:', self.folder_edit)
        filter_layout.addRow('Dates:', date_layout)
        filter_layout.addRow('Maximum results:', self.result_limit)
        main_layout.addWidget(self.filter_panel)
        button_layout = QHBoxLayout()
        self.open_button = QPushButton('Select PST archives...')
        self.search_button = QPushButton('Search')
        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.setEnabled(False)
        for button in (self.open_button, self.search_button, self.cancel_button):
            button_layout.addWidget(button)
        main_layout.addLayout(button_layout)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        self.result_model = QStandardItemModel(0, len(RESULT_COLUMNS), self)
        self.result_model.setHorizontalHeaderLabels(RESULT_COLUMNS)
        self.result_table = QTableView()
        self.result_table.setModel(self.result_model)
        self.result_table.setSortingEnabled(True)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.result_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setPlaceholderText('Select a search result to read the message.')
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.result_table)
        splitter.addWidget(self.preview_edit)
        splitter.setSizes([350, 300])
        main_layout.addWidget(splitter, 1)
        self.report_edit = QPlainTextEdit()
        self.report_edit.setReadOnly(True)
        self.report_edit.setMaximumHeight(110)
        main_layout.addWidget(self.report_edit)
        self.build_menus()
        self.open_button.clicked.connect(self.select_archives)
        self.search_button.clicked.connect(self.start_search)
        self.cancel_button.clicked.connect(self.cancel_search)
        self.query_edit.returnPressed.connect(self.start_search)
        self.result_table.selectionModel().selectionChanged.connect(self.show_selected_message)
        saved_geometry = self.settings.value('geometry')
        if saved_geometry is not None:
            self.restoreGeometry(saved_geometry)
        self.statusBar().showMessage('Ready — source archives are opened read-only.')

    # %%% Standard File / View / Tools / Help menus
    def build_menus(self):
        file_menu = self.menuBar().addMenu('&File')
        self.open_action = file_menu.addAction('Select PST archives...', self.select_archives)
        self.export_action = file_menu.addAction('Export displayed results to CSV...', self.export_csv)
        file_menu.addSeparator()
        file_menu.addAction('Exit', self.close)
        view_menu = self.menuBar().addMenu('&View')
        preview_action = QAction('Show message preview', self, checkable=True, checked=True)
        preview_action.toggled.connect(self.preview_edit.setVisible)
        view_menu.addAction(preview_action)
        view_menu.addAction('Resize result columns', self.result_table.resizeColumnsToContents)
        tools_menu = self.menuBar().addMenu('&Tools')
        self.search_action = tools_menu.addAction('Search', self.start_search)
        tools_menu.addAction('Cancel search', self.cancel_search)
        help_menu = self.menuBar().addMenu('&Help')
        help_menu.addAction('About', self.show_about)

    def show_about(self):
        QMessageBox.about(self, 'About',
            f'{APPLICATION_TITLE}\nVersion {APPLICATION_VERSION}\n'
            'Author / Requested for: W Wallace\nContact: Not supplied\n\n'
            'Read-only PST access: libpff-python / pypff\nGUI: PySide6\n'
            'Body conversion: Python HTMLParser and striprtf\n\n'
            'No Outlook dependency. No attachment-content search.\n'
            'Recipient fields depend on available transport headers.\n'
            'Email content is displayed as text, never executable HTML.')

    @Slot()
    def select_archives(self):
        if self.search_thread is not None:
            return
        filenames, _ = QFileDialog.getOpenFileNames(self, 'Select PST archives', '',
                                                     'Outlook archives (*.pst);;All files (*)')
        if filenames:
            self.archive_paths = list(dict.fromkeys(Path(name).resolve() for name in filenames))
            self.archive_label.setText('\n'.join(str(path) for path in self.archive_paths))

    # %%% Search lifecycle and cooperative cancellation
    @Slot()
    def start_search(self):
        if self.search_thread is not None:
            return
        if not self.archive_paths:
            QMessageBox.information(self, 'Select archives', 'Select one or more PST files first.')
            return
        start_date = self.start_date.date().toPython()
        end_date = self.end_date.date().toPython()
        if self.date_check.isChecked() and start_date > end_date:
            QMessageBox.warning(self, 'Date range', 'Start date must not follow end date.')
            return
        search_options = dict(query=self.query_edit.text().strip(),
            field=self.field_combo.currentText(), phrase=self.phrase_check.isChecked(),
            folder=self.folder_edit.text().strip(), date_enabled=self.date_check.isChecked(),
            start=start_date, end=end_date, limit=self.result_limit.value())
        self.result_model.removeRows(0, self.result_model.rowCount())
        self.preview_edit.clear()
        self.report_edit.clear()
        self.set_busy(True)
        self.search_thread = ArchiveSearchThread(self.archive_paths, search_options, self)
        self.search_thread.records_ready.connect(self.add_records)
        self.search_thread.status_ready.connect(self.statusBar().showMessage)
        self.search_thread.report_ready.connect(self.report_edit.setPlainText)
        self.search_thread.finished.connect(self.search_finished)
        self.search_thread.start()

    def set_busy(self, busy):
        for control in (self.filter_panel, self.open_button, self.search_button,
                        self.open_action, self.search_action, self.export_action):
            control.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.progress_bar.setRange(0, 0 if busy else 1)
        if not busy:
            self.progress_bar.setValue(1)

    @Slot()
    def cancel_search(self):
        if self.search_thread is not None:
            self.search_thread.requestInterruption()
            self.statusBar().showMessage('Cancelling after the current native read finishes...')

    @Slot(list)
    def add_records(self, records):
        # The stored record follows its row when the user sorts the table.
        self.result_table.setSortingEnabled(False)
        for message_record in records:
            row_items = [QStandardItem(message_record[key]) for key in RECORD_KEYS]
            row_items[0].setData(message_record, Qt.ItemDataRole.UserRole)
            self.result_model.appendRow(row_items)
        self.result_table.setSortingEnabled(True)

    @Slot()
    def search_finished(self):
        completed_thread = self.search_thread
        self.search_thread = None
        if completed_thread is not None:
            completed_thread.deleteLater()
        self.set_busy(False)
        self.statusBar().showMessage(
            f'Search stopped. {self.result_model.rowCount():,} results; inspect the report for completeness.')

    def show_selected_message(self, *unused_arguments):
        selected_rows = self.result_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        message_record = selected_rows[0].data(Qt.ItemDataRole.UserRole)
        if not message_record:
            return
        preview_header = '\n'.join(f'{column}: {message_record[key]}'
                                   for column, key in zip(RESULT_COLUMNS, RECORD_KEYS))
        self.preview_edit.setPlainText(
            preview_header + '\n\n' + (message_record['body'] or '[No readable body]') +
            '\n\n--- Original transport headers ---\n' + message_record['headers'])

    # %%% Explicit user-requested export; source archives are never modified
    @Slot()
    def export_csv(self):
        if self.search_thread is not None or not self.result_model.rowCount():
            return
        filename, _ = QFileDialog.getSaveFileName(self, 'Export displayed results',
                                                   'pst_search_results.csv', 'CSV (*.csv)')
        if not filename:
            return
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(RESULT_COLUMNS + ['Body', 'Transport headers'])
                for row_index in range(self.result_model.rowCount()):
                    record = self.result_model.item(row_index, 0).data(Qt.ItemDataRole.UserRole)
                    values = [record[key] for key in RECORD_KEYS + ['body', 'headers']]
                    # Reduce spreadsheet-formula injection from untrusted email.
                    writer.writerow(["'" + value if value.lstrip().startswith(
                        ('=', '+', '-', '@')) else value for value in values])
            self.statusBar().showMessage('Displayed results exported; CSV contains private email content.')
        except OSError as error:
            QMessageBox.critical(self, 'Export failed', str(error))

    def closeEvent(self, event):
        if self.search_thread is not None:
            self.cancel_search()
            QMessageBox.information(self, 'Search stopping',
                'Cancellation requested. Wait for the reader to stop, then close again.\n'
                'The native reader is not forcibly terminated.')
            event.ignore()
            return
        self.settings.setValue('geometry', self.saveGeometry())
        event.accept()


# %% Application entry point / Spyder-compatible QApplication reuse
# Preserve the window reference in the console. Do not create a second Qt app.
# Prefer an external terminal when Spyder has already loaded another Qt binding.
def main():
    global PST_SEARCH_WINDOW
    existing_window = globals().get('PST_SEARCH_WINDOW')
    if existing_window is not None:
        try:
            existing_window.show()
            existing_window.raise_()
            existing_window.activateWindow()
            return
        except RuntimeError:
            pass
    application = QApplication.instance()
    owns_event_loop = application is None
    if application is None:
        application = QApplication(sys.argv)
    PST_SEARCH_WINDOW = PSTSearchWindow()
    PST_SEARCH_WINDOW.show()
    if owns_event_loop:
        application.exec()


if __name__ == '__main__':
    main()
