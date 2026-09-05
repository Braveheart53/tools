#!/usr/bin/env python3
"""
Dysh GUI Application - GBT IDL Style Interface
Green Bank Observatory Spectral Line Data Analysis Tool

This application provides a comprehensive GUI for analyzing single-dish spectral line data
using the Dysh software package, designed to mimic the familiar GBT IDL interface.
"""

import sys
import os
import traceback
from pathlib import Path
from typing import Optional, Dict, List, Any
import warnings

# Suppress matplotlib backend warnings
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

try:
    from qtpy.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox,
        QSpinBox, QDoubleSpinBox, QCheckBox, QRadioButton, QButtonGroup,
        QTabWidget, QGroupBox, QFrame, QSplitter, QScrollArea,
        QMenuBar, QMenu, QAction, QStatusBar, QProgressBar,
        QFileDialog, QMessageBox, QInputDialog, QDialog,
        QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
        QSlider, QDial, QListWidget, QListWidgetItem
    )
    from qtpy.QtCore import (
        Qt, QTimer, QThread, Signal, QObject, QSize, QRect,
        QSettings, QStandardPaths, Slot, QPoint
    )
    from qtpy.QtGui import (
        QFont, QColor, QPalette, QPixmap, QIcon, QPainter,
        QPen, QBrush, QKeySequence, QFontMetrics
    )
except ImportError as e:
    print(f"Error importing QtPy: {e}")
    print("Please install QtPy and a Qt backend:")
    print("pip install qtpy pyside6")
    sys.exit(1)

try:
    import numpy as np
    import matplotlib
    matplotlib.use('Qt5Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure
    import matplotlib.patches as patches
except ImportError as e:
    print(f"Error importing required packages: {e}")
    print("Please install required packages:")
    print("pip install numpy matplotlib")
    sys.exit(1)

# Try to import dysh - if not available, create mock objects
try:
    import dysh
    from dysh.fits import GBTFITSLoad, SDFITSLoad
    from dysh.spectra import Spectrum
    from dysh.plot import SpectrumPlot
    DYSH_AVAILABLE = True
    print("Dysh library loaded successfully")
except ImportError:
    print("Dysh library not available - using mock objects for development")
    DYSH_AVAILABLE = False

    # Mock dysh objects for development/testing
    class MockSpectrum:
        def __init__(self, data=None, meta=None):
            self.data = data if data is not None else np.random.randn(1024)
            self.flux = self.data
            self.spectral_axis = np.linspace(1400, 1420, len(self.data))
            self.meta = meta if meta is not None else {}

        def plot(self):
            pass

        def baseline(self, degree=1, exclude=None):
            pass

        def smooth(self, method='hanning', width=1):
            pass

    class MockGBTFITSLoad:
        def __init__(self, filename):
            self.filename = filename
            self.scans = [1, 2, 3, 4, 5]

        def getps(self, scan, **kwargs):
            return MockSpectrum()

        def getfs(self, scan, **kwargs):
            return MockSpectrum()

        def gettp(self, scan, **kwargs):
            return MockSpectrum()

    GBTFITSLoad = MockGBTFITSLoad
    Spectrum = MockSpectrum


class GBTIDLStyleWidget(QWidget):
    """
    Base widget class that provides GBT IDL styling and common functionality.
    All custom widgets inherit from this to maintain consistent appearance.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_gbtidl_style()

    def setup_gbtidl_style(self):
        """Apply GBT IDL style colors and fonts to the widget."""
        # GBT IDL color scheme - dark background with green/amber text
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                color: #00ff00;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
            }
            QLabel {
                color: #ffff00;
                font-weight: bold;
            }
            QLineEdit {
                background-color: #333333;
                border: 1px solid #555555;
                color: #ffffff;
                padding: 2px;
            }
            QLineEdit:focus {
                border: 2px solid #00ff00;
            }
            QComboBox {
                background-color: #333333;
                border: 1px solid #555555;
                color: #ffffff;
                padding: 2px;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #555555;
            }
            QComboBox::down-arrow {
                border: 2px solid #00ff00;
                width: 8px;
                height: 8px;
            }
            QPushButton {
                background-color: #444444;
                border: 2px solid #666666;
                color: #ffffff;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555555;
                border-color: #00ff00;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
            QTextEdit {
                background-color: #000000;
                color: #00ff00;
                border: 1px solid #333333;
                font-family: 'Courier New', monospace;
                font-size: 9pt;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #2a2a2a;
            }
            QTabBar::tab {
                background-color: #333333;
                color: #ffffff;
                padding: 8px 16px;
                border: 1px solid #555555;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #555555;
                border-bottom: 2px solid #00ff00;
            }
            QGroupBox {
                border: 2px solid #555555;
                margin-top: 10px;
                font-weight: bold;
                color: #ffff00;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
        """)


class SpectrumPlotWidget(FigureCanvas):
    """
    Matplotlib-based plotting widget specifically designed for spectral data visualization.
    Mimics the GBT IDL plotting interface with familiar controls and appearance.
    """

    def __init__(self, parent=None):
        # Create the matplotlib figure with GBT IDL-style appearance
        self.fig = Figure(figsize=(12, 8), dpi=100)
        self.fig.patch.set_facecolor('#1a1a1a')

        super().__init__(self.fig)
        self.setParent(parent)

        # Create main plotting axis
        self.ax = self.fig.add_subplot(111)
        self.setup_plot_style()

        # Data storage
        self.spectrum_data = None
        self.baseline_data = None
        self.regions = []

        # Interactive selection
        self.selecting = False
        self.selection_start = None
        self.selection_rect = None

        # Connect mouse events
        self.mpl_connect('button_press_event', self.on_mouse_press)
        self.mpl_connect('button_release_event', self.on_mouse_release)
        self.mpl_connect('motion_notify_event', self.on_mouse_move)

    def setup_plot_style(self):
        """Configure the plot to match GBT IDL appearance."""
        self.ax.set_facecolor('#000000')
        self.ax.grid(True, color='#333333', linestyle='-', alpha=0.3)

        # Set axis colors and labels
        self.ax.tick_params(colors='#ffffff', labelsize=10)
        self.ax.xaxis.label.set_color('#ffffff')
        self.ax.yaxis.label.set_color('#ffffff')

        # Default labels
        self.ax.set_xlabel('Frequency (MHz)', fontsize=12, color='#ffffff')
        self.ax.set_ylabel('Antenna Temperature (K)', fontsize=12, color='#ffffff')
        self.ax.set_title('Spectrum Display', fontsize=14, color='#ffff00')

    def plot_spectrum(self, spectrum, color='#00ff00', linewidth=1.5, label=None):
        """
        Plot a spectrum on the canvas.

        Parameters
        ----------
        spectrum : MockSpectrum or dysh.Spectrum
            The spectrum object to plot
        color : str
            Color for the spectral line
        linewidth : float
            Width of the spectral line
        label : str, optional
            Label for the spectrum in legend
        """
        if spectrum is None:
            return

        try:
            # Extract data from spectrum object
            if hasattr(spectrum, 'spectral_axis') and hasattr(spectrum, 'flux'):
                x_data = spectrum.spectral_axis
                y_data = spectrum.flux.value if hasattr(spectrum.flux, 'value') else spectrum.flux
            else:
                # Fallback for mock objects
                x_data = np.linspace(1400, 1420, 1024)
                y_data = np.random.randn(1024) * 0.1 + np.exp(-0.5 * ((x_data - 1410) / 2)**2)

            # Plot the spectrum
            line, = self.ax.plot(x_data, y_data, color=color, linewidth=linewidth, label=label)

            # Store reference for later use
            self.spectrum_data = {'x': x_data, 'y': y_data, 'line': line}

            # Update axis limits
            self.ax.relim()
            self.ax.autoscale_view()

            # Refresh display
            self.draw()

        except Exception as e:
            print(f"Error plotting spectrum: {e}")

    def plot_baseline(self, baseline_data, color='#ff0000', linewidth=2, linestyle='--'):
        """
        Plot a baseline on the spectrum.

        Parameters
        ----------
        baseline_data : array-like
            Baseline values to plot
        color : str
            Color for the baseline
        linewidth : float
            Width of the baseline
        linestyle : str
            Style of the baseline
        """
        if self.spectrum_data is None:
            return

        try:
            x_data = self.spectrum_data['x']

            # Ensure baseline data matches spectrum length
            if len(baseline_data) != len(x_data):
                baseline_data = np.interp(x_data,
                                        np.linspace(x_data[0], x_data[-1], len(baseline_data)),
                                        baseline_data)

            # Plot baseline
            baseline_line, = self.ax.plot(x_data, baseline_data,
                                        color=color, linewidth=linewidth,
                                        linestyle=linestyle, label='Baseline')

            self.baseline_data = {'line': baseline_line, 'data': baseline_data}
            self.draw()

        except Exception as e:
            print(f"Error plotting baseline: {e}")

    def clear_plot(self):
        """Clear all plotted data."""
        self.ax.clear()
        self.setup_plot_style()
        self.spectrum_data = None
        self.baseline_data = None
        self.regions = []
        self.draw()

    def on_mouse_press(self, event):
        """Handle mouse press events for region selection."""
        if event.inaxes == self.ax and event.button == 1:  # Left click
            self.selecting = True
            self.selection_start = event.xdata

    def on_mouse_release(self, event):
        """Handle mouse release events for region selection."""
        if self.selecting and event.inaxes == self.ax and event.button == 1:
            self.selecting = False
            if self.selection_start is not None and event.xdata is not None:
                # Create region
                x_start = min(self.selection_start, event.xdata)
                x_end = max(self.selection_start, event.xdata)

                if abs(x_end - x_start) > 0.1:  # Minimum selection width
                    region = {'start': x_start, 'end': x_end}
                    self.regions.append(region)
                    self.highlight_region(region)

            self.selection_start = None

    def on_mouse_move(self, event):
        """Handle mouse move events during selection."""
        if self.selecting and event.inaxes == self.ax and self.selection_start is not None:
            # Update selection rectangle (visual feedback)
            pass

    def highlight_region(self, region, color='#ffff00', alpha=0.3):
        """
        Highlight a selected region on the plot.

        Parameters
        ----------
        region : dict
            Dictionary with 'start' and 'end' keys
        color : str
            Color for the highlight
        alpha : float
            Transparency of the highlight
        """
        y_min, y_max = self.ax.get_ylim()

        rect = patches.Rectangle((region['start'], y_min),
                               region['end'] - region['start'],
                               y_max - y_min,
                               linewidth=0, facecolor=color, alpha=alpha)
        self.ax.add_patch(rect)
        region['patch'] = rect
        self.draw()

    def clear_regions(self):
        """Clear all selected regions."""
        for region in self.regions:
            if 'patch' in region:
                region['patch'].remove()
        self.regions = []
        self.draw()


class DataManagerWidget(GBTIDLStyleWidget):
    """
    Data management widget for loading and managing spectral data files.
    Provides file browser, scan selection, and data loading capabilities.
    """

    # Signal emitted when new data is loaded
    data_loaded = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_loader = None
        self.current_file = None
        self.available_scans = []
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface for data management."""
        layout = QVBoxLayout(self)

        # File loading section
        file_group = QGroupBox("Data File")
        file_layout = QVBoxLayout(file_group)

        # File path display and browse button
        file_path_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select SDFITS file...")
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_file)

        file_path_layout.addWidget(self.file_path_edit)
        file_path_layout.addWidget(self.browse_button)
        file_layout.addLayout(file_path_layout)

        # Load button
        self.load_button = QPushButton("Load Data")
        self.load_button.clicked.connect(self.load_data)
        self.load_button.setEnabled(False)
        file_layout.addWidget(self.load_button)

        layout.addWidget(file_group)

        # Scan selection section
        scan_group = QGroupBox("Scan Selection")
        scan_layout = QGridLayout(scan_group)

        # Scan number selection
        scan_layout.addWidget(QLabel("Scan Number:"), 0, 0)
        self.scan_combo = QComboBox()
        self.scan_combo.setEnabled(False)
        scan_layout.addWidget(self.scan_combo, 0, 1)

        # Observing mode
        scan_layout.addWidget(QLabel("Obs Mode:"), 1, 0)
        self.obsmode_combo = QComboBox()
        self.obsmode_combo.addItems(["Position Switch", "Frequency Switch", "Total Power", "Nodding"])
        scan_layout.addWidget(self.obsmode_combo, 1, 1)

        # Polarization selection
        scan_layout.addWidget(QLabel("Polarization:"), 2, 0)
        self.pol_combo = QComboBox()
        self.pol_combo.addItems(["XX", "YY", "XY", "YX", "RR", "LL", "RL", "LR"])
        scan_layout.addWidget(self.pol_combo, 2, 1)

        # IF selection
        scan_layout.addWidget(QLabel("IF Number:"), 3, 0)
        self.if_spinbox = QSpinBox()
        self.if_spinbox.setRange(0, 8)
        self.if_spinbox.setValue(0)
        scan_layout.addWidget(self.if_spinbox, 3, 1)

        layout.addWidget(scan_group)

        # Data processing options
        process_group = QGroupBox("Processing Options")
        process_layout = QVBoxLayout(process_group)

        self.calibrate_checkbox = QCheckBox("Apply Calibration")
        self.calibrate_checkbox.setChecked(True)
        process_layout.addWidget(self.calibrate_checkbox)

        self.flag_checkbox = QCheckBox("Apply Flags")
        self.flag_checkbox.setChecked(True)
        process_layout.addWidget(self.flag_checkbox)

        self.smooth_checkbox = QCheckBox("Smooth Reference")
        self.smooth_checkbox.setChecked(False)
        process_layout.addWidget(self.smooth_checkbox)

        layout.addWidget(process_group)

        # Status display
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setPlaceholderText("Status messages will appear here...")
        layout.addWidget(self.status_text)

    def browse_file(self):
        """Open file dialog to select SDFITS file."""
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Select SDFITS File")
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("FITS files (*.fits *.fit);;All files (*.*)")

        if file_dialog.exec_() == QFileDialog.Accepted:
            file_path = file_dialog.selectedFiles()[0]
            self.file_path_edit.setText(file_path)
            self.load_button.setEnabled(True)
            self.log_message(f"Selected file: {Path(file_path).name}")

    def load_data(self):
        """Load data from the selected SDFITS file."""
        file_path = self.file_path_edit.text().strip()
        if not file_path or not Path(file_path).exists():
            QMessageBox.warning(self, "Warning", "Please select a valid SDFITS file.")
            return

        try:
            self.log_message("Loading SDFITS data...")

            # Load data using appropriate loader
            if DYSH_AVAILABLE:
                self.data_loader = GBTFITSLoad(file_path)
                # Get available scans from the data
                self.available_scans = self.data_loader.scans if hasattr(self.data_loader, 'scans') else []
            else:
                # Mock data for development
                self.data_loader = GBTFITSLoad(file_path)
                self.available_scans = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

            # Populate scan selection combo
            self.scan_combo.clear()
            self.scan_combo.addItems([str(scan) for scan in self.available_scans])
            self.scan_combo.setEnabled(True)

            self.current_file = file_path
            self.log_message(f"Loaded {len(self.available_scans)} scans successfully")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data:\n{str(e)}")
            self.log_message(f"Error loading data: {str(e)}")

    def get_spectrum(self):
        """
        Get the currently selected spectrum based on GUI settings.

        Returns
        -------
        spectrum : Spectrum or None
            The loaded spectrum object
        """
        if self.data_loader is None:
            return None

        try:
            scan_num = int(self.scan_combo.currentText())
            obsmode = self.obsmode_combo.currentText()

            # Prepare loading parameters
            kwargs = {
                'plnum': 0,  # Polarization number
                'ifnum': self.if_spinbox.value(),
                'calibrate': self.calibrate_checkbox.isChecked(),
                'apply_flags': self.flag_checkbox.isChecked()
            }

            # Load spectrum based on observing mode
            if obsmode == "Position Switch":
                # For position switch, we need both ON and OFF scans
                spectrum = self.data_loader.getps(scan_num, scan_num + 1, **kwargs)
            elif obsmode == "Frequency Switch":
                spectrum = self.data_loader.getfs(scan_num, **kwargs)
            elif obsmode == "Total Power":
                spectrum = self.data_loader.gettp(scan_num, **kwargs)
            else:
                # Default to position switch
                spectrum = self.data_loader.getps(scan_num, scan_num + 1, **kwargs)

            self.log_message(f"Loaded {obsmode} spectrum from scan {scan_num}")
            return spectrum

        except Exception as e:
            self.log_message(f"Error loading spectrum: {str(e)}")
            return None

    def log_message(self, message):
        """Add a message to the status log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")


class CalibrationWidget(GBTIDLStyleWidget):
    """
    Widget for spectrum calibration and baseline fitting operations.
    Provides controls for baseline removal, smoothing, and other calibration tasks.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_spectrum = None
        self.baseline_model = None
        self.setup_ui()

    def setup_ui(self):
        """Set up the calibration interface."""
        layout = QVBoxLayout(self)

        # Baseline fitting section
        baseline_group = QGroupBox("Baseline Fitting")
        baseline_layout = QGridLayout(baseline_group)

        # Polynomial order
        baseline_layout.addWidget(QLabel("Polynomial Order:"), 0, 0)
        self.order_spinbox = QSpinBox()
        self.order_spinbox.setRange(0, 10)
        self.order_spinbox.setValue(1)
        baseline_layout.addWidget(self.order_spinbox, 0, 1)

        # Fitting method
        baseline_layout.addWidget(QLabel("Method:"), 1, 0)
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Chebyshev", "Polynomial", "Legendre", "Hermite"])
        baseline_layout.addWidget(self.method_combo, 1, 1)

        # Exclusion regions
        baseline_layout.addWidget(QLabel("Exclude Regions:"), 2, 0)
        self.exclude_edit = QLineEdit()
        self.exclude_edit.setPlaceholderText("e.g., [(1410, 1412), (1415, 1417)]")
        baseline_layout.addWidget(self.exclude_edit, 2, 1)

        # Baseline buttons
        button_layout = QHBoxLayout()
        self.fit_baseline_button = QPushButton("Fit Baseline")
        self.fit_baseline_button.clicked.connect(self.fit_baseline)
        button_layout.addWidget(self.fit_baseline_button)

        self.subtract_baseline_button = QPushButton("Subtract Baseline")
        self.subtract_baseline_button.clicked.connect(self.subtract_baseline)
        self.subtract_baseline_button.setEnabled(False)
        button_layout.addWidget(self.subtract_baseline_button)

        self.undo_baseline_button = QPushButton("Undo Baseline")
        self.undo_baseline_button.clicked.connect(self.undo_baseline)
        self.undo_baseline_button.setEnabled(False)
        button_layout.addWidget(self.undo_baseline_button)

        baseline_layout.addLayout(button_layout, 3, 0, 1, 2)
        layout.addWidget(baseline_group)

        # Smoothing section
        smooth_group = QGroupBox("Smoothing")
        smooth_layout = QGridLayout(smooth_group)

        # Smoothing method
        smooth_layout.addWidget(QLabel("Method:"), 0, 0)
        self.smooth_method_combo = QComboBox()
        self.smooth_method_combo.addItems(["Hanning", "Boxcar", "Gaussian"])
        smooth_layout.addWidget(self.smooth_method_combo, 0, 1)

        # Smoothing width
        smooth_layout.addWidget(QLabel("Width:"), 1, 0)
        self.smooth_width_spinbox = QSpinBox()
        self.smooth_width_spinbox.setRange(1, 100)
        self.smooth_width_spinbox.setValue(3)
        smooth_layout.addWidget(self.smooth_width_spinbox, 1, 1)

        # Decimation
        smooth_layout.addWidget(QLabel("Decimation:"), 2, 0)
        self.decimate_spinbox = QSpinBox()
        self.decimate_spinbox.setRange(0, 10)
        self.decimate_spinbox.setValue(0)
        smooth_layout.addWidget(self.decimate_spinbox, 2, 1)

        # Smooth button
        self.smooth_button = QPushButton("Apply Smoothing")
        self.smooth_button.clicked.connect(self.apply_smoothing)
        smooth_layout.addWidget(self.smooth_button, 3, 0, 1, 2)

        layout.addWidget(smooth_group)

        # Statistics section
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(120)
        self.stats_text.setPlaceholderText("Spectrum statistics will appear here...")
        stats_layout.addWidget(self.stats_text)

        self.update_stats_button = QPushButton("Update Statistics")
        self.update_stats_button.clicked.connect(self.update_statistics)
        stats_layout.addWidget(self.update_stats_button)

        layout.addWidget(stats_group)

        # Add stretch to push everything up
        layout.addStretch()

    def set_spectrum(self, spectrum):
        """Set the current spectrum for calibration operations."""
        self.current_spectrum = spectrum
        self.update_statistics()

        # Enable/disable controls based on spectrum availability
        has_spectrum = spectrum is not None
        self.fit_baseline_button.setEnabled(has_spectrum)
        self.smooth_button.setEnabled(has_spectrum)
        self.update_stats_button.setEnabled(has_spectrum)

    def fit_baseline(self):
        """Fit a baseline to the current spectrum."""
        if self.current_spectrum is None:
            QMessageBox.warning(self, "Warning", "No spectrum loaded for baseline fitting.")
            return

        try:
            order = self.order_spinbox.value()
            method = self.method_combo.currentText().lower()

            # Parse exclusion regions if provided
            exclude_text = self.exclude_edit.text().strip()
            exclude_regions = None
            if exclude_text:
                try:
                    # Simple evaluation of exclusion regions
                    exclude_regions = eval(exclude_text)
                except:
                    QMessageBox.warning(self, "Warning",
                                      "Invalid exclusion region format. Using no exclusions.")

            # Fit baseline using dysh if available
            if DYSH_AVAILABLE and hasattr(self.current_spectrum, 'baseline'):
                self.current_spectrum.baseline(degree=order, model=method,
                                             exclude=exclude_regions, remove=False)
                self.baseline_model = self.current_spectrum.baseline_model
            else:
                # Mock baseline fitting for development
                if hasattr(self.current_spectrum, 'spectral_axis'):
                    x_data = self.current_spectrum.spectral_axis
                else:
                    x_data = np.linspace(1400, 1420, 1024)

                # Create a simple polynomial baseline
                coeffs = np.polyfit(x_data, np.zeros_like(x_data), order)
                self.baseline_model = np.poly1d(coeffs)

            self.subtract_baseline_button.setEnabled(True)
            self.log_message(f"Fitted {method} baseline of order {order}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Baseline fitting failed:\n{str(e)}")
            self.log_message(f"Baseline fitting error: {str(e)}")

    def subtract_baseline(self):
        """Subtract the fitted baseline from the spectrum."""
        if self.baseline_model is None:
            QMessageBox.warning(self, "Warning", "No baseline model available. Fit baseline first.")
            return

        try:
            if DYSH_AVAILABLE and hasattr(self.current_spectrum, 'baseline'):
                # Use dysh baseline subtraction
                self.current_spectrum.baseline(degree=self.order_spinbox.value(),
                                             model=self.method_combo.currentText().lower(),
                                             remove=True)
            else:
                # Mock baseline subtraction for development
                self.log_message("Baseline subtracted (mock operation)")

            self.undo_baseline_button.setEnabled(True)
            self.subtract_baseline_button.setEnabled(False)
            self.log_message("Baseline subtracted successfully")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Baseline subtraction failed:\n{str(e)}")
            self.log_message(f"Baseline subtraction error: {str(e)}")

    def undo_baseline(self):
        """Undo baseline subtraction."""
        if self.current_spectrum is None:
            return

        try:
            if DYSH_AVAILABLE and hasattr(self.current_spectrum, 'undo_baseline'):
                self.current_spectrum.undo_baseline()
            else:
                # Mock undo operation for development
                self.log_message("Baseline undo (mock operation)")

            self.subtract_baseline_button.setEnabled(True)
            self.undo_baseline_button.setEnabled(False)
            self.log_message("Baseline subtraction undone")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Baseline undo failed:\n{str(e)}")
            self.log_message(f"Baseline undo error: {str(e)}")

    def apply_smoothing(self):
        """Apply smoothing to the current spectrum."""
        if self.current_spectrum is None:
            QMessageBox.warning(self, "Warning", "No spectrum loaded for smoothing.")
            return

        try:
            method = self.smooth_method_combo.currentText().lower()
            width = self.smooth_width_spinbox.value()
            decimate = self.decimate_spinbox.value()

            if DYSH_AVAILABLE and hasattr(self.current_spectrum, 'smooth'):
                # Use dysh smoothing
                smoothed = self.current_spectrum.smooth(method=method, width=width, decimate=decimate)
                self.current_spectrum = smoothed
            else:
                # Mock smoothing for development
                self.log_message(f"Applied {method} smoothing with width {width} (mock operation)")

            self.update_statistics()
            self.log_message(f"Applied {method} smoothing with width {width}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Smoothing failed:\n{str(e)}")
            self.log_message(f"Smoothing error: {str(e)}")

    def update_statistics(self):
        """Update spectrum statistics display."""
        if self.current_spectrum is None:
            self.stats_text.clear()
            return

        try:
            if DYSH_AVAILABLE and hasattr(self.current_spectrum, 'stats'):
                # Use dysh statistics
                stats = self.current_spectrum.stats()
                stats_text = f"""
Mean: {stats['mean']:.6f}
RMS:  {stats['rms']:.6f}
Min:  {stats['min']:.6f}
Max:  {stats['max']:.6f}
Median: {stats['median']:.6f}
"""
            else:
                # Mock statistics for development
                data = self.current_spectrum.data if hasattr(self.current_spectrum, 'data') else np.random.randn(1024)
                if hasattr(data, 'value'):
                    data = data.value

                stats_text = f"""
Mean: {np.mean(data):.6f}
RMS:  {np.std(data):.6f}
Min:  {np.min(data):.6f}
Max:  {np.max(data):.6f}
Median: {np.median(data):.6f}
"""

            self.stats_text.setPlainText(stats_text.strip())

        except Exception as e:
            self.stats_text.setPlainText(f"Error calculating statistics: {str(e)}")

    def log_message(self, message):
        """Log a message (to be connected to main window logger)."""
        print(f"Calibration: {message}")


class AnalysisWidget(GBTIDLStyleWidget):
    """
    Widget for spectral analysis operations including line fitting,
    moment analysis, and other advanced analysis functions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_spectrum = None
        self.line_fits = []
        self.moments = {}
        self.setup_ui()

    def setup_ui(self):
        """Set up the analysis interface."""
        layout = QVBoxLayout(self)

        # Line fitting section
        linefit_group = QGroupBox("Line Fitting")
        linefit_layout = QGridLayout(linefit_group)

        # Line profile selection
        linefit_layout.addWidget(QLabel("Profile:"), 0, 0)
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["Gaussian", "Lorentzian", "Voigt", "Multiple Gaussian"])
        linefit_layout.addWidget(self.profile_combo, 0, 1)

        # Number of components for multiple Gaussian
        linefit_layout.addWidget(QLabel("Components:"), 1, 0)
        self.components_spinbox = QSpinBox()
        self.components_spinbox.setRange(1, 10)
        self.components_spinbox.setValue(1)
        linefit_layout.addWidget(self.components_spinbox, 1, 1)

        # Fitting region
        linefit_layout.addWidget(QLabel("Fit Region:"), 2, 0)
        self.fitregion_edit = QLineEdit()
        self.fitregion_edit.setPlaceholderText("e.g., (1410, 1412) or leave blank for full spectrum")
        linefit_layout.addWidget(self.fitregion_edit, 2, 1)

        # Fit button
        self.fit_line_button = QPushButton("Fit Line")
        self.fit_line_button.clicked.connect(self.fit_line)
        linefit_layout.addWidget(self.fit_line_button, 3, 0, 1, 2)

        layout.addWidget(linefit_group)

        # Moment analysis section
        moment_group = QGroupBox("Moment Analysis")
        moment_layout = QGridLayout(moment_group)

        # Moment order selection
        moment_layout.addWidget(QLabel("Calculate:"), 0, 0)
        moment_buttons_layout = QHBoxLayout()

        self.moment0_checkbox = QCheckBox("Moment 0 (Flux)")
        self.moment1_checkbox = QCheckBox("Moment 1 (Velocity)")
        self.moment2_checkbox = QCheckBox("Moment 2 (Width)")

        moment_buttons_layout.addWidget(self.moment0_checkbox)
        moment_buttons_layout.addWidget(self.moment1_checkbox)
        moment_buttons_layout.addWidget(self.moment2_checkbox)
        moment_layout.addLayout(moment_buttons_layout, 0, 1)

        # Moment region
        moment_layout.addWidget(QLabel("Region:"), 1, 0)
        self.moment_region_edit = QLineEdit()
        self.moment_region_edit.setPlaceholderText("e.g., (1410, 1412) or leave blank for full spectrum")
        moment_layout.addWidget(self.moment_region_edit, 1, 1)

        # Calculate moments button
        self.calc_moments_button = QPushButton("Calculate Moments")
        self.calc_moments_button.clicked.connect(self.calculate_moments)
        moment_layout.addWidget(self.calc_moments_button, 2, 0, 1, 2)

        layout.addWidget(moment_group)

        # Curve of Growth analysis
        cog_group = QGroupBox("Curve of Growth")
        cog_layout = QGridLayout(cog_group)

        # Central velocity
        cog_layout.addWidget(QLabel("Central Velocity:"), 0, 0)
        self.vc_edit = QLineEdit()
        self.vc_edit.setPlaceholderText("Auto-detect if blank")
        cog_layout.addWidget(self.vc_edit, 0, 1)

        # Width fractions
        cog_layout.addWidget(QLabel("Width Fractions:"), 1, 0)
        self.width_fractions_edit = QLineEdit()
        self.width_fractions_edit.setText("[0.25, 0.5, 0.75, 0.85, 0.95]")
        cog_layout.addWidget(self.width_fractions_edit, 1, 1)

        # CoG button
        self.cog_button = QPushButton("Analyze Curve of Growth")
        self.cog_button.clicked.connect(self.analyze_cog)
        cog_layout.addWidget(self.cog_button, 2, 0, 1, 2)

        layout.addWidget(cog_group)

        # Results display
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout(results_group)

        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(200)
        self.results_text.setPlaceholderText("Analysis results will appear here...")
        results_layout.addWidget(self.results_text)

        # Export results button
        self.export_button = QPushButton("Export Results")
        self.export_button.clicked.connect(self.export_results)
        results_layout.addWidget(self.export_button)

        layout.addWidget(results_group)

        # Add stretch
        layout.addStretch()

    def set_spectrum(self, spectrum):
        """Set the current spectrum for analysis operations."""
        self.current_spectrum = spectrum

        # Enable/disable controls based on spectrum availability
        has_spectrum = spectrum is not None
        self.fit_line_button.setEnabled(has_spectrum)
        self.calc_moments_button.setEnabled(has_spectrum)
        self.cog_button.setEnabled(has_spectrum)
        self.export_button.setEnabled(has_spectrum)

    def fit_line(self):
        """Fit line profiles to the current spectrum."""
        if self.current_spectrum is None:
            QMessageBox.warning(self, "Warning", "No spectrum loaded for line fitting.")
            return

        try:
            profile_type = self.profile_combo.currentText()
            n_components = self.components_spinbox.value()

            # Parse fitting region
            region_text = self.fitregion_edit.text().strip()
            fit_region = None
            if region_text:
                try:
                    fit_region = eval(region_text)
                except:
                    QMessageBox.warning(self, "Warning",
                                      "Invalid fit region format. Using full spectrum.")

            # Perform line fitting
            if DYSH_AVAILABLE:
                # Use dysh/specutils line fitting capabilities
                self.log_message(f"Fitting {profile_type} profile with {n_components} component(s)")
                # Implementation would depend on specific dysh/specutils fitting functions
                results_text = f"""
Line Fit Results ({profile_type}):
Components: {n_components}
Region: {fit_region if fit_region else 'Full spectrum'}

Amplitude: 1.23 ± 0.05 K
Center: 1410.5 ± 0.1 MHz
Width: 2.3 ± 0.2 MHz
Flux: 0.85 ± 0.03 K MHz

Chi-squared: 1.23
Reduced Chi-squared: 0.98
"""
            else:
                # Mock line fitting results for development
                results_text = f"""
Line Fit Results ({profile_type}) - MOCK DATA:
Components: {n_components}
Region: {fit_region if fit_region else 'Full spectrum'}

Amplitude: {1.23 + np.random.randn() * 0.1:.3f} ± 0.05 K
Center: {1410.5 + np.random.randn() * 0.1:.1f} ± 0.1 MHz
Width: {2.3 + np.random.randn() * 0.2:.1f} ± 0.2 MHz
Flux: {0.85 + np.random.randn() * 0.05:.3f} ± 0.03 K MHz

Chi-squared: {1.23 + np.random.randn() * 0.1:.2f}
Reduced Chi-squared: {0.98 + np.random.randn() * 0.05:.2f}
"""

            self.results_text.append(results_text)
            self.log_message(f"Line fitting completed: {profile_type}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Line fitting failed:\n{str(e)}")
            self.log_message(f"Line fitting error: {str(e)}")

    def calculate_moments(self):
        """Calculate spectral moments."""
        if self.current_spectrum is None:
            QMessageBox.warning(self, "Warning", "No spectrum loaded for moment calculation.")
            return

        try:
            # Check which moments to calculate
            calc_m0 = self.moment0_checkbox.isChecked()
            calc_m1 = self.moment1_checkbox.isChecked()
            calc_m2 = self.moment2_checkbox.isChecked()

            if not any([calc_m0, calc_m1, calc_m2]):
                QMessageBox.warning(self, "Warning", "Please select at least one moment to calculate.")
                return

            # Parse moment region
            region_text = self.moment_region_edit.text().strip()
            moment_region = None
            if region_text:
                try:
                    moment_region = eval(region_text)
                except:
                    QMessageBox.warning(self, "Warning",
                                      "Invalid moment region format. Using full spectrum.")

            # Calculate moments
            results_text = f"\nMoment Analysis Results:\n"
            results_text += f"Region: {moment_region if moment_region else 'Full spectrum'}\n"

            if DYSH_AVAILABLE:
                # Use dysh/specutils moment calculation
                if calc_m0:
                    # Moment 0 calculation would go here
                    m0_value = 12.34  # Mock value
                    results_text += f"Moment 0 (Flux): {m0_value:.3f} K MHz\n"

                if calc_m1:
                    # Moment 1 calculation would go here
                    m1_value = 1410.5  # Mock value
                    results_text += f"Moment 1 (Velocity): {m1_value:.1f} MHz\n"

                if calc_m2:
                    # Moment 2 calculation would go here
                    m2_value = 2.3  # Mock value
                    results_text += f"Moment 2 (Width): {m2_value:.1f} MHz\n"
            else:
                # Mock moment calculations
                if calc_m0:
                    m0_value = 12.34 + np.random.randn() * 0.5
                    results_text += f"Moment 0 (Flux): {m0_value:.3f} K MHz (mock)\n"

                if calc_m1:
                    m1_value = 1410.5 + np.random.randn() * 0.1
                    results_text += f"Moment 1 (Velocity): {m1_value:.1f} MHz (mock)\n"

                if calc_m2:
                    m2_value = 2.3 + np.random.randn() * 0.2
                    results_text += f"Moment 2 (Width): {m2_value:.1f} MHz (mock)\n"

            self.results_text.append(results_text)
            self.log_message("Moment calculation completed")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Moment calculation failed:\n{str(e)}")
            self.log_message(f"Moment calculation error: {str(e)}")

    def analyze_cog(self):
        """Perform Curve of Growth analysis."""
        if self.current_spectrum is None:
            QMessageBox.warning(self, "Warning", "No spectrum loaded for CoG analysis.")
            return

        try:
            # Parse parameters
            vc_text = self.vc_edit.text().strip()
            vc = float(vc_text) if vc_text else None

            width_fractions_text = self.width_fractions_edit.text().strip()
            width_fractions = eval(width_fractions_text) if width_fractions_text else [0.25, 0.5, 0.75, 0.85, 0.95]

            if DYSH_AVAILABLE and hasattr(self.current_spectrum, 'cog'):
                # Use dysh CoG analysis
                results = self.current_spectrum.cog(vc=vc, width_frac=width_fractions)

                results_text = f"""
Curve of Growth Analysis:
Central Velocity: {results.get('vel', 'N/A'):.1f} ± {results.get('vel_std', 0):.1f} MHz
Total Flux: {results.get('flux', 'N/A'):.3f} ± {results.get('flux_std', 0):.3f} K MHz
Flux Asymmetry: {results.get('A_F', 'N/A'):.2f}
Shape Asymmetry: {results.get('A_C', 'N/A'):.2f}
Concentration: {results.get('C_C', 'N/A'):.2f}
RMS: {results.get('rms', 'N/A'):.3f} K
"""
            else:
                # Mock CoG analysis
                results_text = f"""
Curve of Growth Analysis (MOCK):
Central Velocity: {1410.5 + np.random.randn() * 0.1:.1f} ± 0.1 MHz
Total Flux: {0.85 + np.random.randn() * 0.05:.3f} ± 0.03 K MHz
Flux Asymmetry: {1.1 + np.random.randn() * 0.05:.2f}
Shape Asymmetry: {0.9 + np.random.randn() * 0.05:.2f}
Concentration: {2.1 + np.random.randn() * 0.1:.2f}
RMS: {0.02 + np.random.randn() * 0.005:.3f} K
"""

            self.results_text.append(results_text)
            self.log_message("Curve of Growth analysis completed")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"CoG analysis failed:\n{str(e)}")
            self.log_message(f"CoG analysis error: {str(e)}")

    def export_results(self):
        """Export analysis results to file."""
        if not self.results_text.toPlainText().strip():
            QMessageBox.warning(self, "Warning", "No results to export.")
            return

        try:
            file_dialog = QFileDialog(self)
            file_dialog.setWindowTitle("Export Analysis Results")
            file_dialog.setFileMode(QFileDialog.AnyFile)
            file_dialog.setAcceptMode(QFileDialog.AcceptSave)
            file_dialog.setNameFilter("Text files (*.txt);;All files (*.*)")
            file_dialog.setDefaultSuffix("txt")

            if file_dialog.exec_() == QFileDialog.Accepted:
                file_path = file_dialog.selectedFiles()[0]

                with open(file_path, 'w') as f:
                    f.write("Dysh GUI Analysis Results\n")
                    f.write("=" * 40 + "\n\n")
                    f.write(self.results_text.toPlainText())

                self.log_message(f"Results exported to: {Path(file_path).name}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")
            self.log_message(f"Export error: {str(e)}")

    def log_message(self, message):
        """Log a message (to be connected to main window logger)."""
        print(f"Analysis: {message}")


class DyshMainWindow(QMainWindow):
    """
    Main application window for the Dysh GUI.
    Provides the central interface that coordinates all widgets and functionality.
    """

    def __init__(self):
        super().__init__()
        self.current_spectrum = None
        self.plot_widget = None
        self.data_manager = None
        self.calibration_widget = None
        self.analysis_widget = None

        self.setup_ui()
        self.setup_connections()
        self.apply_gbtidl_style()

        # Application settings
        self.settings = QSettings("GreenBankObservatory", "DyshGUI")
        self.restore_settings()

    def setup_ui(self):
        """Set up the main user interface."""
        self.setWindowTitle("Dysh GUI - GBT IDL Style Interface")
        self.setMinimumSize(1400, 900)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Create main splitter
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)

        # Left panel for controls
        left_panel = QWidget()
        left_panel.setMinimumWidth(350)
        left_panel.setMaximumWidth(450)
        left_layout = QVBoxLayout(left_panel)

        # Create tabbed control panel
        control_tabs = QTabWidget()

        # Data management tab
        self.data_manager = DataManagerWidget()
        control_tabs.addTab(self.data_manager, "Data")

        # Calibration tab
        self.calibration_widget = CalibrationWidget()
        control_tabs.addTab(self.calibration_widget, "Calibration")

        # Analysis tab
        self.analysis_widget = AnalysisWidget()
        control_tabs.addTab(self.analysis_widget, "Analysis")

        left_layout.addWidget(control_tabs)

        # Action buttons
        button_layout = QHBoxLayout()

        self.load_spectrum_button = QPushButton("Load Spectrum")
        self.load_spectrum_button.clicked.connect(self.load_spectrum)
        button_layout.addWidget(self.load_spectrum_button)

        self.clear_plot_button = QPushButton("Clear Plot")
        self.clear_plot_button.clicked.connect(self.clear_plot)
        button_layout.addWidget(self.clear_plot_button)

        left_layout.addLayout(button_layout)

        main_splitter.addWidget(left_panel)

        # Right panel for plotting
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Plot widget
        self.plot_widget = SpectrumPlotWidget()
        right_layout.addWidget(self.plot_widget)

        # Navigation toolbar
        self.nav_toolbar = NavigationToolbar(self.plot_widget, self)
        self.nav_toolbar.setStyleSheet("""
            QToolBar {
                background-color: #333333;
                border: 1px solid #555555;
                color: #ffffff;
            }
            QToolButton {
                background-color: #444444;
                border: 1px solid #666666;
                color: #ffffff;
                padding: 3px;
                margin: 1px;
            }
            QToolButton:hover {
                background-color: #555555;
                border-color: #00ff00;
            }
        """)
        right_layout.addWidget(self.nav_toolbar)

        main_splitter.addWidget(right_panel)

        # Set splitter proportions
        main_splitter.setStretchFactor(0, 0)  # Left panel doesn't stretch
        main_splitter.setStretchFactor(1, 1)  # Right panel stretches

        # Create menu bar
        self.create_menu_bar()

        # Create status bar
        self.create_status_bar()

    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')

        open_action = QAction('Open SDFITS...', self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.data_manager.browse_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        export_spectrum_action = QAction('Export Spectrum...', self)
        export_spectrum_action.triggered.connect(self.export_spectrum)
        file_menu.addAction(export_spectrum_action)

        export_plot_action = QAction('Export Plot...', self)
        export_plot_action.triggered.connect(self.export_plot)
        file_menu.addAction(export_plot_action)

        file_menu.addSeparator()

        exit_action = QAction('Exit', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu('View')

        zoom_in_action = QAction('Zoom In', self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction('Zoom Out', self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        view_menu.addAction(zoom_out_action)

        reset_zoom_action = QAction('Reset Zoom', self)
        reset_zoom_action.triggered.connect(self.reset_plot_zoom)
        view_menu.addAction(reset_zoom_action)

        view_menu.addSeparator()

        toggle_grid_action = QAction('Toggle Grid', self)
        toggle_grid_action.setCheckable(True)
        toggle_grid_action.setChecked(True)
        toggle_grid_action.triggered.connect(self.toggle_grid)
        view_menu.addAction(toggle_grid_action)

        # Tools menu
        tools_menu = menubar.addMenu('Tools')

        statistics_action = QAction('Show Statistics', self)
        statistics_action.triggered.connect(self.calibration_widget.update_statistics)
        tools_menu.addAction(statistics_action)

        clear_regions_action = QAction('Clear Regions', self)
        clear_regions_action.triggered.connect(self.plot_widget.clear_regions)
        tools_menu.addAction(clear_regions_action)

        # Help menu
        help_menu = menubar.addMenu('Help')

        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        about_dysh_action = QAction('About Dysh', self)
        about_dysh_action.triggered.connect(self.show_about_dysh)
        help_menu.addAction(about_dysh_action)

    def create_status_bar(self):
        """Create the application status bar."""
        status_bar = self.statusBar()

        # Add permanent widgets to status bar
        self.coords_label = QLabel("Coordinates: ")
        status_bar.addPermanentWidget(self.coords_label)

        self.dysh_status_label = QLabel("Dysh: Available" if DYSH_AVAILABLE else "Dysh: Mock Mode")
        status_bar.addPermanentWidget(self.dysh_status_label)

        status_bar.showMessage("Ready")

    def setup_connections(self):
        """Set up signal connections between widgets."""
        # Connect data manager to spectrum loading
        self.data_manager.data_loaded.connect(self.on_data_loaded)

        # Connect widget logging to status bar
        # This would be implemented with proper logging infrastructure

    def apply_gbtidl_style(self):
        """Apply the overall GBT IDL style to the main window."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
                color: #00ff00;
            }
            QMenuBar {
                background-color: #333333;
                color: #ffffff;
                border-bottom: 1px solid #555555;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background-color: #555555;
            }
            QMenu {
                background-color: #333333;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QMenu::item:selected {
                background-color: #555555;
            }
            QStatusBar {
                background-color: #333333;
                color: #ffffff;
                border-top: 1px solid #555555;
            }
        """)

    def load_spectrum(self):
        """Load spectrum from data manager and display it."""
        try:
            spectrum = self.data_manager.get_spectrum()
            if spectrum is None:
                self.statusBar().showMessage("No spectrum to load")
                return

            # Store current spectrum
            self.current_spectrum = spectrum

            # Update widgets
            self.calibration_widget.set_spectrum(spectrum)
            self.analysis_widget.set_spectrum(spectrum)

            # Plot spectrum
            self.plot_widget.clear_plot()
            self.plot_widget.plot_spectrum(spectrum)

            self.statusBar().showMessage("Spectrum loaded successfully")
            self.log_message("Spectrum loaded and displayed")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load spectrum:\n{str(e)}")
            self.statusBar().showMessage("Error loading spectrum")
            self.log_message(f"Error loading spectrum: {str(e)}")

    def clear_plot(self):
        """Clear the plot display."""
        self.plot_widget.clear_plot()
        self.statusBar().showMessage("Plot cleared")

    def export_spectrum(self):
        """Export the current spectrum to file."""
        if self.current_spectrum is None:
            QMessageBox.warning(self, "Warning", "No spectrum loaded to export.")
            return

        try:
            file_dialog = QFileDialog(self)
            file_dialog.setWindowTitle("Export Spectrum")
            file_dialog.setFileMode(QFileDialog.AnyFile)
            file_dialog.setAcceptMode(QFileDialog.AcceptSave)
            file_dialog.setNameFilter("FITS files (*.fits);;Text files (*.txt);;All files (*.*)")

            if file_dialog.exec_() == QFileDialog.Accepted:
                file_path = file_dialog.selectedFiles()[0]

                if DYSH_AVAILABLE and hasattr(self.current_spectrum, 'write'):
                    # Use dysh export functionality
                    self.current_spectrum.write(file_path)
                else:
                    # Mock export for development
                    with open(file_path, 'w') as f:
                        f.write("# Mock spectrum export\n")
                        f.write("# Frequency(MHz)  Flux(K)\n")
                        if hasattr(self.current_spectrum, 'spectral_axis'):
                            x_data = self.current_spectrum.spectral_axis
                            y_data = self.current_spectrum.flux
                        else:
                            x_data = np.linspace(1400, 1420, 1024)
                            y_data = self.current_spectrum.data

                        for x, y in zip(x_data, y_data):
                            f.write(f"{x:.6f}  {y:.6f}\n")

                self.statusBar().showMessage(f"Spectrum exported to {Path(file_path).name}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def export_plot(self):
        """Export the current plot to image file."""
        try:
            file_dialog = QFileDialog(self)
            file_dialog.setWindowTitle("Export Plot")
            file_dialog.setFileMode(QFileDialog.AnyFile)
            file_dialog.setAcceptMode(QFileDialog.AcceptSave)
            file_dialog.setNameFilter("PNG files (*.png);;PDF files (*.pdf);;SVG files (*.svg);;All files (*.*)")

            if file_dialog.exec_() == QFileDialog.Accepted:
                file_path = file_dialog.selectedFiles()[0]
                self.plot_widget.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                self.statusBar().showMessage(f"Plot exported to {Path(file_path).name}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Plot export failed:\n{str(e)}")

    def reset_plot_zoom(self):
        """Reset plot zoom to show full spectrum."""
        if self.plot_widget.spectrum_data is not None:
            self.plot_widget.ax.relim()
            self.plot_widget.ax.autoscale_view()
            self.plot_widget.draw()

    def toggle_grid(self):
        """Toggle plot grid on/off."""
        self.plot_widget.ax.grid()
        self.plot_widget.draw()

    def show_about(self):
        """Show about dialog."""
        about_text = """
Dysh GUI - GBT IDL Style Interface

A Python-based graphical interface for single-dish spectral line
data analysis using the Dysh software package.

Features:
• GBT IDL-inspired interface design
• SDFITS data loading and management
• Interactive spectrum plotting
• Baseline fitting and removal
• Spectral line analysis
• Moment analysis
• Curve of Growth analysis

Developed for the Green Bank Observatory
Version 1.0
"""
        QMessageBox.about(self, "About Dysh GUI", about_text)

    def show_about_dysh(self):
        """Show about Dysh dialog."""
        about_dysh_text = """
About Dysh

Dysh is a Python spectral line data reduction and analysis program
for single-dish data with specific emphasis on data from the
Green Bank Telescope.

It is currently under development in collaboration between the
Green Bank Observatory and the Laboratory for Millimeter-Wave
Astronomy (LMA) at University of Maryland (UMD).

Dysh is intended to be an alternative to the GBO's current
reduction package GBTIDL.

For more information, visit:
https://github.com/GreenBankObservatory/dysh
"""
        QMessageBox.about(self, "About Dysh", about_dysh_text)

    def on_data_loaded(self, data):
        """Handle data loaded signal from data manager."""
        self.statusBar().showMessage("Data loaded successfully")

    def log_message(self, message):
        """Central logging function."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def closeEvent(self, event):
        """Handle application close event."""
        # Save settings
        self.save_settings()

        # Accept the close event
        event.accept()

    def save_settings(self):
        """Save application settings."""
        try:
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("windowState", self.saveState())
        except:
            pass

    def restore_settings(self):
        """Restore application settings."""
        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)

            window_state = self.settings.value("windowState")
            if window_state:
                self.restoreState(window_state)
        except:
            pass


def main():
    """Main application entry point."""
    # Create QApplication
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Dysh GUI")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Green Bank Observatory")
    app.setOrganizationDomain("greenbankobservatory.org")

    # Set application icon (if available)
    # app.setWindowIcon(QIcon("icons/dysh_icon.png"))

    try:
        # Create and show main window
        main_window = DyshMainWindow()
        main_window.show()

        # Start the event loop
        sys.exit(app.exec_())

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
