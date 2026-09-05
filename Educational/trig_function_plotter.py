import sys
import math
import re
from dataclasses import dataclass

import numpy as np
from qtpy import API_NAME
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


SAFE_FUNCTIONS = {
    'sin': np.sin,
    'cos': np.cos,
    'tan': np.tan,
    'sinh': np.sinh,
    'cosh': np.cosh,
    'tanh': np.tanh,
    'arcsin': np.arcsin,
    'arccos': np.arccos,
    'arctan': np.arctan,
    'asin': np.arcsin,
    'acos': np.arccos,
    'atan': np.arctan,
    'exp': np.exp,
    'log': np.log,
    'log10': np.log10,
    'sqrt': np.sqrt,
    'abs': np.abs,
    'floor': np.floor,
    'ceil': np.ceil,
    'round': np.round,
    'pi': np.pi,
    'e': np.e,
}


@dataclass
class CurveSpec:
    enabled: bool
    name: str
    kind: str
    amplitude: float
    inside_expr: str
    outside_expr: str
    color: str
    width: float


class MplCanvas(FigureCanvas):
    def __init__(self):
        self.figure = Figure(figsize=(8, 6), tight_layout=True)
        self.axes = self.figure.add_subplot(111)
        super().__init__(self.figure)


class CurveRow:
    def __init__(self, parent, defaults=None):
        defaults = defaults or {}
        self.widget = QWidget()
        layout = QGridLayout(self.widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(4)

        self.enabled = QCheckBox('On')
        self.enabled.setChecked(defaults.get('enabled', True))

        self.name = QLineEdit(defaults.get('name', 'curve'))
        self.kind = QComboBox()
        self.kind.addItems(['sin', 'cos', 'tan', 'sinh', 'cosh', 'tanh'])
        self.kind.setCurrentText(defaults.get('kind', 'sin'))

        self.amplitude = QDoubleSpinBox()
        self.amplitude.setRange(-1e6, 1e6)
        self.amplitude.setDecimals(4)
        self.amplitude.setValue(defaults.get('amplitude', 1.0))
        self.amplitude.setSingleStep(0.1)

        self.inside_expr = QLineEdit(defaults.get('inside_expr', 'x'))
        self.outside_expr = QLineEdit(defaults.get('outside_expr', '0'))

        self.width = QDoubleSpinBox()
        self.width.setRange(0.1, 20.0)
        self.width.setDecimals(1)
        self.width.setValue(defaults.get('width', 2.0))

        self.color = QColor(defaults.get('color', '#1f77b4'))
        self.color_button = QPushButton()
        self.color_button.clicked.connect(self.pick_color)
        self._update_button_color()

        self.remove_button = QPushButton('Remove')

        widgets = [
            (QLabel('Enable'), 0, 0), (self.enabled, 0, 1),
            (QLabel('Label'), 0, 2), (self.name, 0, 3),
            (QLabel('Type'), 0, 4), (self.kind, 0, 5),
            (QLabel('Amp'), 0, 6), (self.amplitude, 0, 7),
            (QLabel('Inside'), 1, 0), (self.inside_expr, 1, 1, 1, 3),
            (QLabel('Outside'), 1, 4), (self.outside_expr, 1, 5, 1, 2),
            (QLabel('Width'), 1, 7), (self.width, 1, 8),
            (QLabel('Color'), 0, 8), (self.color_button, 0, 9),
            (self.remove_button, 1, 9),
        ]

        for item in widgets:
            if len(item) == 3:
                layout.addWidget(item[0], item[1], item[2])
            else:
                layout.addWidget(item[0], item[1], item[2], item[3], item[4])

    def pick_color(self):
        color = QColorDialog.getColor(self.color, self.widget, 'Choose curve color')
        if color.isValid():
            self.color = color
            self._update_button_color()

    def _update_button_color(self):
        self.color_button.setText(self.color.name())
        self.color_button.setStyleSheet(
            'QPushButton {background:%s; color:%s; padding:4px 8px; border:1px solid #666;}'
            % (self.color.name(), '#ffffff' if self.color.lightness() < 128 else '#000000')
        )

    def spec(self):
        return CurveSpec(
            enabled=self.enabled.isChecked(),
            name=self.name.text().strip() or self.kind.currentText(),
            kind=self.kind.currentText(),
            amplitude=self.amplitude.value(),
            inside_expr=self.inside_expr.text().strip() or 'x',
            outside_expr=self.outside_expr.text().strip() or '0',
            color=self.color.name(),
            width=self.width.value(),
        )


class FunctionPlotter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f'Trig / Hyperbolic Plotter - Qt via {API_NAME}')
        self.resize(1400, 850)
        self.rows = []
        self._build_ui()
        self.add_curve({'name': 'sin(x)', 'kind': 'sin', 'inside_expr': 'x', 'color': '#1f77b4'})
        self.add_curve({'name': 'cos(2*x)', 'kind': 'cos', 'inside_expr': '2*x', 'color': '#d62728'})
        self.plot_curves()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        domain_box = QGroupBox('Domain and Sampling')
        domain_form = QFormLayout(domain_box)
        self.x_min = QDoubleSpinBox(); self.x_min.setRange(-1e6, 1e6); self.x_min.setValue(-10.0)
        self.x_max = QDoubleSpinBox(); self.x_max.setRange(-1e6, 1e6); self.x_max.setValue(10.0)
        self.samples = QSpinBox(); self.samples.setRange(100, 200000); self.samples.setValue(4000)
        self.degrees = QCheckBox('Interpret x in degrees')
        self.show_grid = QCheckBox('Show grid'); self.show_grid.setChecked(True)
        self.show_legend = QCheckBox('Show legend'); self.show_legend.setChecked(True)
        domain_form.addRow('x min', self.x_min)
        domain_form.addRow('x max', self.x_max)
        domain_form.addRow('Samples', self.samples)
        domain_form.addRow(self.degrees)
        domain_form.addRow(self.show_grid)
        domain_form.addRow(self.show_legend)
        left_layout.addWidget(domain_box)

        curves_box = QGroupBox('Curves')
        self.curves_layout = QVBoxLayout(curves_box)
        left_layout.addWidget(curves_box, 1)

        button_row = QHBoxLayout()
        add_btn = QPushButton('Add curve')
        add_btn.clicked.connect(lambda: self.add_curve())
        plot_btn = QPushButton('Plot')
        plot_btn.clicked.connect(self.plot_curves)
        export_btn = QPushButton('Export PNG')
        export_btn.clicked.connect(self.export_png)
        button_row.addWidget(add_btn)
        button_row.addWidget(plot_btn)
        button_row.addWidget(export_btn)
        left_layout.addLayout(button_row)

        help_box = QGroupBox('Expression Help')
        help_layout = QVBoxLayout(help_box)
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText(
            'Build functions in the form: y = A * func( inside_expr ) + outside_expr\n\n'
            'Examples:\n'
            '  sin(x)\n'
            '  2*cos(3*x + pi/4)  -> enter A=2, type=cos, inside=3*x + pi/4\n'
            '  tan(x/2) + 1       -> type=tan, inside=x/2, outside=1\n'
            '  sinh(0.5*x)\n'
            '  cos(x**2)\n'
            '  sin(exp(-0.1*x)*x)\n\n'
            'Allowed names: x, pi, e, sin, cos, tan, sinh, cosh, tanh,\n'
            'arcsin/asin, arccos/acos, arctan/atan, exp, log, log10, sqrt, abs, floor, ceil, round\n\n'
            'Use Python-style powers: x**2\n'
            'You can overlay as many curves as you like.'
        )
        help_layout.addWidget(help_text)
        left_layout.addWidget(help_box)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.canvas = MplCanvas()
        self.toolbar = NavigationToolbar(self.canvas, self)
        right_layout.addWidget(self.toolbar)
        right_layout.addWidget(self.canvas, 1)

        self.value_table = QTableWidget(0, 3)
        self.value_table.setHorizontalHeaderLabels(['Curve', 'Min y', 'Max y'])
        self.value_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        right_layout.addWidget(self.value_table)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([520, 880])

        for widget in (self.x_min, self.x_max, self.samples, self.degrees, self.show_grid, self.show_legend):
            signal = getattr(widget, 'valueChanged', None) or getattr(widget, 'stateChanged', None)
            signal.connect(self.plot_curves)

    def add_curve(self, defaults=None):
        row = CurveRow(self, defaults=defaults)
        row.remove_button.clicked.connect(lambda: self.remove_curve(row))
        for widget in (row.enabled, row.kind, row.amplitude, row.inside_expr, row.outside_expr, row.width):
            signal = getattr(widget, 'valueChanged', None) or getattr(widget, 'currentTextChanged', None) or getattr(widget, 'textChanged', None) or getattr(widget, 'stateChanged', None)
            signal.connect(self.plot_curves)
        self.rows.append(row)
        self.curves_layout.addWidget(row.widget)

    def remove_curve(self, row):
        if row in self.rows:
            self.rows.remove(row)
            row.widget.setParent(None)
            row.widget.deleteLater()
            self.plot_curves()

    def safe_eval(self, expr, x):
        expr = expr.strip()
        if not expr:
            return np.zeros_like(x)
        if '__' in expr:
            raise ValueError('Double underscore is not allowed.')
        if re.search(r'[^\w\d\s\+\-\*/\(\)\.,\^]', expr):
            raise ValueError('Expression contains unsupported characters.')
        expr = expr.replace('^', '**')
        env = dict(SAFE_FUNCTIONS)
        env['x'] = x
        return eval(expr, {'__builtins__': {}}, env)

    def plot_curves(self):
        try:
            x0, x1 = self.x_min.value(), self.x_max.value()
            if x0 >= x1:
                raise ValueError('x min must be smaller than x max.')
            x = np.linspace(x0, x1, self.samples.value())
            x_for_expr = np.deg2rad(x) if self.degrees.isChecked() else x

            ax = self.canvas.axes
            ax.clear()
            self.value_table.setRowCount(0)

            for row in self.rows:
                spec = row.spec()
                if not spec.enabled:
                    continue

                inside = self.safe_eval(spec.inside_expr, x_for_expr)
                if spec.kind == 'sin':
                    y = spec.amplitude * np.sin(inside)
                elif spec.kind == 'cos':
                    y = spec.amplitude * np.cos(inside)
                elif spec.kind == 'tan':
                    y = spec.amplitude * np.tan(inside)
                elif spec.kind == 'sinh':
                    y = spec.amplitude * np.sinh(inside)
                elif spec.kind == 'cosh':
                    y = spec.amplitude * np.cosh(inside)
                elif spec.kind == 'tanh':
                    y = spec.amplitude * np.tanh(inside)
                else:
                    raise ValueError('Unsupported function type.')

                y = y + self.safe_eval(spec.outside_expr, x_for_expr)
                y = np.array(y, dtype=float)
                y[~np.isfinite(y)] = np.nan

                finite = np.isfinite(y)
                if spec.kind == 'tan':
                    jump = np.abs(np.diff(y)) > 10 * max(1.0, np.nanstd(y[finite]) if np.any(finite) else 1.0)
                    y[np.where(jump)[0] + 1] = np.nan

                ax.plot(x, y, label=spec.name, color=spec.color, linewidth=spec.width)
                self._append_stats(spec.name, y)

            ax.set_xlabel('x (degrees)' if self.degrees.isChecked() else 'x (radians / raw units)')
            ax.set_ylabel('y')
            ax.set_title('Trigonometric and Hyperbolic Function Plotter')
            if self.show_grid.isChecked():
                ax.grid(True, alpha=0.35)
            if self.show_legend.isChecked():
                ax.legend(loc='best')
            self.canvas.draw_idle()
            self.statusBar().showMessage('Plot updated', 2000)
        except Exception as exc:
            self.statusBar().showMessage(str(exc), 5000)

    def _append_stats(self, name, y):
        valid = y[np.isfinite(y)]
        r = self.value_table.rowCount()
        self.value_table.insertRow(r)
        if valid.size:
            min_text = f'{np.min(valid):.6g}'
            max_text = f'{np.max(valid):.6g}'
        else:
            min_text = 'n/a'
            max_text = 'n/a'
        for c, text in enumerate([name, min_text, max_text]):
            self.value_table.setItem(r, c, QTableWidgetItem(text))

    def export_png(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Export plot', 'plot.png', 'PNG Files (*.png)')
        if filename:
            self.canvas.figure.savefig(filename, dpi=150)
            self.statusBar().showMessage(f'Saved {filename}', 4000)


def main():
    app = QApplication(sys.argv)
    win = FunctionPlotter()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
