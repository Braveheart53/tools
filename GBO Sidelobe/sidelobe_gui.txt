#!/usr/bin/env python3
"""
QtPy-based GUI for the sidelobe radio astronomy program.
Provides a user-friendly interface for sidelobe computation and stray radiation correction.
"""

import sys
import os
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging
import threading
import subprocess

try:
    from qtpy.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QTabWidget, QGroupBox, QLabel, QLineEdit, QPushButton,
        QCheckBox, QRadioButton, QButtonGroup, QSpinBox, QDoubleSpinBox,
        QComboBox, QTextEdit, QProgressBar, QFileDialog, QMessageBox,
        QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
        QScrollArea, QFrame, QSlider, QFormLayout
    )
    from qtpy.QtCore import Qt, QThread, Signal, QTimer, QSettings
    from qtpy.QtGui import QFont, QIcon, QPalette, QPixmap, QTextCursor
    QTPY_AVAILABLE = True
except ImportError:
    QTPY_AVAILABLE = False
    print("QtPy not available. GUI functionality disabled.")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Matplotlib not available. Plotting functionality disabled.")

# Import our sidelobe computation module
try:
    from sidelobe import SidelobeComputer, ScanData, TelescopeType, ProcessingMode
    import numpy as np
except ImportError as e:
    print(f"Error importing sidelobe module: {e}")
    sys.exit(1)


class ProcessingThread(QThread):
    """Background thread for sidelobe processing"""

    progress_updated = Signal(int)
    status_updated = Signal(str)
    finished_processing = Signal(bool, str)  # success, message

    def __init__(self, computer, input_file, output_file, parameters):
        super().__init__()
        self.computer = computer
        self.input_file = input_file
        self.output_file = output_file
        self.parameters = parameters
        self._stop_requested = False

    def stop(self):
        """Request thread to stop"""
        self._stop_requested = True

    def run(self):
        """Run the processing in background thread"""
        try:
            self.status_updated.emit("Loading input file...")
            self.progress_updated.emit(10)

            if self._stop_requested:
                return

            # Load scans
            scans = self.computer.load_sdfits_file(self.input_file)
            self.status_updated.emit(f"Loaded {len(scans)} scans")
            self.progress_updated.emit(30)

            if self._stop_requested:
                return

            # Apply processing based on parameters
            if self.parameters['mode'] == 'extract':
                output_scans = scans
                self.status_updated.emit("Extracting scans...")
            elif self.parameters['mode'] == 'correct':
                self.status_updated.emit("Computing stray corrections...")
                self.progress_updated.emit(50)
                stray_scans = self.computer.compute_sidelobe_correction(
                    scans, self.parameters['telescope_type']
                )
                self.progress_updated.emit(70)
                output_scans = self.computer.apply_stray_correction(scans, stray_scans)
            else:  # compute mode
                self.status_updated.emit("Computing sidelobes...")
                self.progress_updated.emit(50)
                output_scans = self.computer.compute_sidelobe_correction(
                    scans, self.parameters['telescope_type']
                )

            if self._stop_requested:
                return

            # Save results
            self.status_updated.emit("Saving output file...")
            self.progress_updated.emit(90)
            self.computer.save_sdfits_file(
                output_scans, self.output_file,
                overwrite=self.parameters['overwrite']
            )

            self.progress_updated.emit(100)
            self.status_updated.emit("Processing completed successfully")
            self.finished_processing.emit(True, "Processing completed successfully")

        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            self.status_updated.emit(error_msg)
            self.finished_processing.emit(False, error_msg)


class ScanTableWidget(QTableWidget):
    """Custom table widget for displaying scan information"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_table()

    def setup_table(self):
        """Setup table columns and properties"""
        columns = ['Scan', 'Object', 'RA', 'DEC', 'GLON', 'GLAT', 'Date-Obs']
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)

        # Configure table appearance
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSortingEnabled(True)

    def populate_scans(self, scans: List[ScanData]):
        """Populate table with scan data"""
        self.setRowCount(len(scans))

        for row, scan in enumerate(scans):
            self.setItem(row, 0, QTableWidgetItem(str(scan.scan_number)))
            self.setItem(row, 1, QTableWidgetItem(scan.object_name))
            self.setItem(row, 2, QTableWidgetItem(f"{scan.ra:.5f}"))
            self.setItem(row, 3, QTableWidgetItem(f"{scan.dec:.5f}"))
            self.setItem(row, 4, QTableWidgetItem(f"{scan.glon:.3f}"))
            self.setItem(row, 5, QTableWidgetItem(f"{scan.glat:.3f}"))
            self.setItem(row, 6, QTableWidgetItem(scan.date_obs))

        self.resizeColumnsToContents()


class PlotWidget(QWidget):
    """Widget for plotting spectra and sidelobe data"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup plotting interface"""
        if not MATPLOTLIB_AVAILABLE:
            layout = QVBoxLayout()
            label = QLabel("Matplotlib not available - plotting disabled")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            self.setLayout(layout)
            return

        layout = QVBoxLayout()

        # Create matplotlib figure and canvas
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

        # Add control buttons
        controls = QHBoxLayout()
        self.plot_spectrum_btn = QPushButton("Plot Spectrum")
        self.plot_sidelobe_btn = QPushButton("Plot Sidelobe")
        self.clear_plot_btn = QPushButton("Clear")

        self.plot_spectrum_btn.clicked.connect(self.plot_spectrum)
        self.plot_sidelobe_btn.clicked.connect(self.plot_sidelobe)
        self.clear_plot_btn.clicked.connect(self.clear_plot)

        controls.addWidget(self.plot_spectrum_btn)
        controls.addWidget(self.plot_sidelobe_btn)
        controls.addWidget(self.clear_plot_btn)
        controls.addStretch()

        layout.addLayout(controls)
        self.setLayout(layout)

        # Store for current scan data
        self.current_scans = []

    def set_scans(self, scans: List[ScanData]):
        """Set current scan data for plotting"""
        self.current_scans = scans

    def plot_spectrum(self):
        """Plot first spectrum"""
        if not MATPLOTLIB_AVAILABLE or not self.current_scans:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        scan = self.current_scans[0]
        ax.plot(scan.velocity, scan.spectrum, 'b-', linewidth=1.0)
        ax.set_xlabel('Velocity (km/s)')
        ax.set_ylabel('Temperature (K)')
        ax.set_title(f'Spectrum: {scan.object_name} (Scan {scan.scan_number})')
        ax.grid(True, alpha=0.3)

        self.canvas.draw()

    def plot_sidelobe(self):
        """Plot sidelobe pattern (placeholder)"""
        if not MATPLOTLIB_AVAILABLE:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Generate sample sidelobe pattern
        theta = np.linspace(0, 180, 1000)
        # Simple beam pattern model
        pattern = np.cos(np.radians(theta/10))**2 * np.exp(-theta/30)
        pattern[theta > 90] *= 0.01  # Far sidelobes

        ax.semilogy(theta, pattern, 'r-', linewidth=2.0)
        ax.set_xlabel('Angle (degrees)')
        ax.set_ylabel('Beam Response')
        ax.set_title('Telescope Sidelobe Pattern (Sample)')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(1e-6, 1)

        self.canvas.draw()

    def clear_plot(self):
        """Clear current plot"""
        if MATPLOTLIB_AVAILABLE:
            self.figure.clear()
            self.canvas.draw()


class SidelobeGUI(QMainWindow):
    """Main GUI application window"""

    def __init__(self):
        super().__init__()
        self.computer = SidelobeComputer()
        self.processing_thread = None
        self.current_scans = []
        self.settings = QSettings('SidelobeGUI', 'SidelobeGUI')

        self.setup_ui()
        self.setup_logging()
        self.restore_settings()

    def setup_ui(self):
        """Setup the main user interface"""
        self.setWindowTitle("Sidelobe Radio Astronomy Tool")
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Create splitter for resizable panes
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left pane - controls
        controls_widget = self.create_controls_widget()
        splitter.addWidget(controls_widget)

        # Right pane - tabs for results, plots, logs
        tabs_widget = self.create_tabs_widget()
        splitter.addWidget(tabs_widget)

        # Set splitter proportions
        splitter.setSizes([400, 800])

        # Setup status bar
        self.statusBar().showMessage("Ready")

        # Setup progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)

    def create_controls_widget(self) -> QWidget:
        """Create the controls panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QGridLayout(file_group)

        # Input file
        file_layout.addWidget(QLabel("Input File:"), 0, 0)
        self.input_file_edit = QLineEdit()
        self.input_browse_btn = QPushButton("Browse...")
        self.input_browse_btn.clicked.connect(self.browse_input_file)
        file_layout.addWidget(self.input_file_edit, 0, 1)
        file_layout.addWidget(self.input_browse_btn, 0, 2)

        # Output file
        file_layout.addWidget(QLabel("Output File:"), 1, 0)
        self.output_file_edit = QLineEdit()
        self.output_browse_btn = QPushButton("Browse...")
        self.output_browse_btn.clicked.connect(self.browse_output_file)
        file_layout.addWidget(self.output_file_edit, 1, 1)
        file_layout.addWidget(self.output_browse_btn, 1, 2)

        layout.addWidget(file_group)

        # Processing options group
        processing_group = QGroupBox("Processing Options")
        processing_layout = QVBoxLayout(processing_group)

        # Processing mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Compute Sidelobes",
            "Apply Stray Correction",
            "Extract Scans"
        ])
        mode_layout.addWidget(self.mode_combo)
        processing_layout.addLayout(mode_layout)

        # Telescope type
        telescope_layout = QHBoxLayout()
        telescope_layout.addWidget(QLabel("Telescope:"))
        self.telescope_combo = QComboBox()
        self.telescope_combo.addItems(["Auto-detect", "GBT", "NRAO 140-foot"])
        telescope_layout.addWidget(self.telescope_combo)
        processing_layout.addLayout(telescope_layout)

        # Options checkboxes
        self.overwrite_cb = QCheckBox("Overwrite output file")
        self.force_cb = QCheckBox("Force processing")
        self.quiet_cb = QCheckBox("Quiet mode")

        processing_layout.addWidget(self.overwrite_cb)
        processing_layout.addWidget(self.force_cb)
        processing_layout.addWidget(self.quiet_cb)

        layout.addWidget(processing_group)

        # Advanced options group
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QFormLayout(advanced_group)

        self.calibration_edit = QLineEdit()
        self.calibration_edit.setPlaceholderText("1.0")
        advanced_layout.addRow("Calibration Factor:", self.calibration_edit)

        self.scan_range_start = QSpinBox()
        self.scan_range_start.setRange(0, 999999)
        self.scan_range_end = QSpinBox()
        self.scan_range_end.setRange(0, 999999)
        scan_range_layout = QHBoxLayout()
        scan_range_layout.addWidget(self.scan_range_start)
        scan_range_layout.addWidget(QLabel("to"))
        scan_range_layout.addWidget(self.scan_range_end)
        advanced_layout.addRow("Scan Range:", scan_range_layout)

        self.object_filter_edit = QLineEdit()
        self.object_filter_edit.setPlaceholderText("e.g., NGC*")
        advanced_layout.addRow("Object Filter:", self.object_filter_edit)

        layout.addWidget(advanced_group)

        # Action buttons
        button_layout = QVBoxLayout()

        self.load_btn = QPushButton("Load & Preview")
        self.load_btn.clicked.connect(self.load_preview)

        self.process_btn = QPushButton("Start Processing")
        self.process_btn.clicked.connect(self.start_processing)
        self.process_btn.setStyleSheet("QPushButton { font-weight: bold; }")

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)

        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.stop_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        return widget

    def create_tabs_widget(self) -> QTabWidget:
        """Create the tabs widget for results and plots"""
        tabs = QTabWidget()

        # Scan data tab
        self.scan_table = ScanTableWidget()
        tabs.addTab(self.scan_table, "Scan Data")

        # Plots tab
        self.plot_widget = PlotWidget()
        tabs.addTab(self.plot_widget, "Plots")

        # Log tab
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        tabs.addTab(self.log_text, "Log")

        return tabs

    def setup_logging(self):
        """Setup logging to display in GUI"""
        class GuiLogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                self.text_widget.append(msg)
                # Auto-scroll to bottom
                cursor = self.text_widget.textCursor()
                cursor.movePosition(QTextCursor.End)
                self.text_widget.setTextCursor(cursor)

        # Add GUI handler to logger
        gui_handler = GuiLogHandler(self.log_text)
        gui_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logging.getLogger().addHandler(gui_handler)
        logging.getLogger().setLevel(logging.INFO)

    def browse_input_file(self):
        """Browse for input file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Input File", "",
            "FITS files (*.fits *.fit);;All files (*.*)"
        )
        if filename:
            self.input_file_edit.setText(filename)

    def browse_output_file(self):
        """Browse for output file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Select Output File", "",
            "FITS files (*.fits *.fit);;All files (*.*)"
        )
        if filename:
            self.output_file_edit.setText(filename)

    def load_preview(self):
        """Load input file and show preview"""
        input_file = self.input_file_edit.text().strip()
        if not input_file:
            QMessageBox.warning(self, "Warning", "Please select an input file")
            return

        if not os.path.exists(input_file):
            QMessageBox.error(self, "Error", f"Input file not found: {input_file}")
            return

        try:
            self.statusBar().showMessage("Loading file...")
            QApplication.processEvents()

            self.current_scans = self.computer.load_sdfits_file(input_file)
            self.scan_table.populate_scans(self.current_scans)
            self.plot_widget.set_scans(self.current_scans)

            self.statusBar().showMessage(f"Loaded {len(self.current_scans)} scans")

        except Exception as e:
            QMessageBox.error(self, "Error", f"Failed to load file:\n{str(e)}")
            self.statusBar().showMessage("Error loading file")

    def start_processing(self):
        """Start background processing"""
        # Validate inputs
        input_file = self.input_file_edit.text().strip()
        output_file = self.output_file_edit.text().strip()

        if not input_file or not output_file:
            QMessageBox.warning(self, "Warning", "Please specify input and output files")
            return

        if not os.path.exists(input_file):
            QMessageBox.error(self, "Error", f"Input file not found: {input_file}")
            return

        if input_file == output_file:
            QMessageBox.error(self, "Error", "Input and output files cannot be the same")
            return

        if os.path.exists(output_file) and not self.overwrite_cb.isChecked():
            reply = QMessageBox.question(
                self, "File Exists",
                f"Output file exists: {output_file}\n\nOverwrite?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Determine processing parameters
        parameters = {
            'mode': ['compute', 'correct', 'extract'][self.mode_combo.currentIndex()],
            'telescope_type': [TelescopeType.AUTO, TelescopeType.GBT, TelescopeType.NRAO_140][self.telescope_combo.currentIndex()],
            'overwrite': self.overwrite_cb.isChecked() or os.path.exists(output_file),
            'force': self.force_cb.isChecked(),
            'quiet': self.quiet_cb.isChecked()
        }

        # Start processing thread
        self.processing_thread = ProcessingThread(
            self.computer, input_file, output_file, parameters
        )

        # Connect signals
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.status_updated.connect(self.update_status)
        self.processing_thread.finished_processing.connect(self.processing_finished)

        # Update UI state
        self.process_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Start processing
        self.processing_thread.start()

    def stop_processing(self):
        """Stop background processing"""
        if self.processing_thread:
            self.processing_thread.stop()
            self.processing_thread.wait(5000)  # Wait up to 5 seconds
            if self.processing_thread.isRunning():
                self.processing_thread.terminate()
                self.processing_thread.wait(2000)

        self.processing_finished(False, "Processing stopped by user")

    def update_progress(self, value: int):
        """Update progress bar"""
        self.progress_bar.setValue(value)

    def update_status(self, message: str):
        """Update status bar message"""
        self.statusBar().showMessage(message)

    def processing_finished(self, success: bool, message: str):
        """Handle processing completion"""
        # Reset UI state
        self.process_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)

        # Show completion message
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Processing Failed", message)

        self.statusBar().showMessage("Ready")

        # Clean up thread
        if self.processing_thread:
            self.processing_thread.deleteLater()
            self.processing_thread = None

    def save_settings(self):
        """Save current settings"""
        self.settings.setValue("input_file", self.input_file_edit.text())
        self.settings.setValue("output_file", self.output_file_edit.text())
        self.settings.setValue("mode", self.mode_combo.currentIndex())
        self.settings.setValue("telescope", self.telescope_combo.currentIndex())
        self.settings.setValue("overwrite", self.overwrite_cb.isChecked())
        self.settings.setValue("force", self.force_cb.isChecked())
        self.settings.setValue("quiet", self.quiet_cb.isChecked())
        self.settings.setValue("geometry", self.saveGeometry())

    def restore_settings(self):
        """Restore saved settings"""
        self.input_file_edit.setText(self.settings.value("input_file", ""))
        self.output_file_edit.setText(self.settings.value("output_file", ""))
        self.mode_combo.setCurrentIndex(int(self.settings.value("mode", 0)))
        self.telescope_combo.setCurrentIndex(int(self.settings.value("telescope", 0)))
        self.overwrite_cb.setChecked(self.settings.value("overwrite", False, type=bool))
        self.force_cb.setChecked(self.settings.value("force", False, type=bool))
        self.quiet_cb.setChecked(self.settings.value("quiet", False, type=bool))

        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        """Handle application close"""
        # Stop any running processing
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            self.processing_thread.wait(3000)

        # Save settings
        self.save_settings()
        event.accept()


def main():
    """Main GUI application entry point"""
    if not QTPY_AVAILABLE:
        print("QtPy not available. Cannot start GUI.")
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("Sidelobe GUI")
    app.setOrganizationName("Radio Astronomy Tools")

    # Set application style
    app.setStyle('Fusion')

    try:
        window = SidelobeGUI()
        window.show()
        return app.exec_()
    except Exception as e:
        print(f"Error starting GUI: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
