#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chromecast Gen 1 Provisioner 1.0.4 — HTTP communication console.
Original author: William W. Wallace, Adaptive Electrodynamics LLC.
Dependencies: qtpy, PySide6, requests, cryptography.
Console reports application-layer HTTP, not a packet capture. Sensitive mode
is opt-in. Review logs before sharing; device responses may identify your device.
"""
import os
import sys
import json
import base64
import re
import time
from datetime import datetime
import requests
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_der_public_key
from cryptography.hazmat.primitives.asymmetric import rsa, padding
os.environ['QT_API'] = 'pyside6'
from qtpy.QtCore import QObject, QThread, Signal, Slot, Qt
from qtpy.QtGui import QFontDatabase, QTextCursor
from qtpy.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QCheckBox, QPlainTextEdit,
    QMessageBox, QFileDialog, QSplitter)


class SetupError(Exception):
    pass


class HttpConsole:
    """Formats prepared HTTP messages; default redaction is best-effort."""
    SECRET_KEYS = {'password', 'passwd', 'enc_passwd', 'psk', 'passphrase',
                   'authorization', 'proxy-authorization', 'cookie', 'set-cookie',
                   'access_token', 'refresh_token', 'token'}

    def __init__(self, emit, sensitive=False):
        self.emit = emit
        self.sensitive = sensitive
        self.secrets = set()

    def remember(self, value):
        if value:
            text = str(value)
            self.secrets.add(text)
            self.secrets.add(json.dumps(text, ensure_ascii=True)[1:-1])

    def clean(self, value):
        if isinstance(value, dict):
            return {k: ('<redacted>' if str(k).lower() in self.SECRET_KEYS else self.clean(v))
                    for k, v in value.items()}
        if isinstance(value, list):
            return [self.clean(v) for v in value]
        return value

    def scrub(self, text):
        if self.sensitive:
            return text
        for secret in sorted(self.secrets, key=len, reverse=True):
            text = text.replace(secret, '<redacted>')
        return text

    def body(self, value):
        if value is None or value == b'' or value == '':
            return '<empty body>'
        if isinstance(value, bytes):
            try:
                text = value.decode('utf-8')
            except UnicodeDecodeError:
                return '<binary body, base64>\n' + base64.b64encode(value).decode('ascii')
        else:
            text = str(value)
        if self.sensitive:
            return text
        try:
            return self.scrub(json.dumps(self.clean(json.loads(text)), ensure_ascii=False, indent=2))
        except (ValueError, TypeError):
            # Non-JSON responses: known values and common labeled fields only.
            text = re.sub(r'(?i)((?:password|passwd|enc_passwd|passphrase|access_token|refresh_token)\s*[=:]\s*)[^\s<>,;]+',
                          r'\1<redacted>', text)
            return self.scrub(text)

    def headers(self, headers):
        return '\n'.join(f'{k}: ' + ('<redacted>' if not self.sensitive and
            k.lower() in self.SECRET_KEYS else self.scrub(str(v))) for k, v in headers.items())

    def write(self, title, text):
        stamp = datetime.now().astimezone().isoformat(timespec='milliseconds')
        self.emit(f'[{stamp}] {title}\n{text}\n' + '-' * 78)

    def request(self, prepared):
        self.write('SEND', f'{prepared.method} {self.scrub(prepared.url)}\n'
                   f'{self.headers(prepared.headers)}\n\n{self.body(prepared.body)}')

    def response(self, response, elapsed):
        self.write('RECEIVE', f'HTTP {response.status_code} {response.reason}; '
                   f'{elapsed:.3f} s; {len(response.content)} body bytes\n'
                   f'{self.headers(response.headers)}\n\n{self.body(response.content)}')

    def error(self, exc):
        self.write('TRANSPORT ERROR', self.scrub(f'{type(exc).__name__}: {exc}'))


def load_key(value):
    if not isinstance(value, str):
        raise SetupError('Missing or invalid public_key in device response.')
    text = value.strip().replace('\\r\\n', '\n').replace('\\n', '\n')
    try:
        if text.startswith('-----BEGIN '):
            key = load_pem_public_key(text.encode('ascii'))
        else:
            text = ''.join(text.split())
            key = load_der_public_key(base64.b64decode(text + '=' * (-len(text) % 4), validate=True))
    except Exception as exc:
        raise SetupError('Device public_key is not valid PEM/Base64 DER.') from exc
    if not isinstance(key, rsa.RSAPublicKey):
        raise SetupError('Device key is not RSA.')
    return key


def security(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise SetupError('Missing/invalid device security number.')
    try:
        result = int(value)
    except ValueError as exc:
        raise SetupError('Security values must be non-negative integers.') from exc
    if result < 0:
        raise SetupError('Security values must be non-negative integers.')
    return result


class SetupClient:
    def __init__(self, url, console, session=None, sleep=time.sleep):
        if not url.startswith('http://'):
            raise SetupError('Use the original HTTP setup URL (normally http://192.168.255.249:8008).')
        self.url = url.rstrip('/')
        self.console, self.sleep = console, sleep
        self.session = session if session is not None else requests.Session()
        self.session.trust_env = False
        self.session.headers.update({'User-Agent': 'curl/7.68.0', 'Accept': 'application/json'})
        self.accepted = False

    def close(self):
        self.session.close()

    def request(self, method, endpoint, payload=None):
        request = requests.Request(method, self.url + endpoint, json=payload)
        prepared = self.session.prepare_request(request)
        self.console.request(prepared)
        start = time.monotonic()
        try:
            response = self.session.send(prepared, timeout=(5, 15), allow_redirects=False)
        except requests.RequestException as exc:
            self.console.error(exc)
            raise SetupError(f'{method} {endpoint}: {type(exc).__name__}. '
                             'Result may be unconfirmed; check the TV before retrying.') from exc
        self.console.response(response, time.monotonic() - start)
        if not 200 <= response.status_code < 300:
            state = 'Connect was accepted; save is unconfirmed.' if self.accepted else 'No save request was sent.'
            raise SetupError(f'{method} {endpoint}: HTTP {response.status_code}. {state} '
                             'See the response body in the console. No automatic retry performed.')
        return response

    def json(self, method, path, payload=None):
        response = self.request(method, path, payload)
        try:
            return response.json()
        except ValueError as exc:
            raise SetupError(f'{path}: response is not valid JSON; see console.') from exc

    def scan(self):
        self.request('POST', '/setup/scan_wifi', {})
        self.console.write('INFO', 'Waiting 12 seconds for Wi-Fi scan results.')
        self.sleep(12)
        rows = self.json('GET', '/setup/scan_results')
        if isinstance(rows, dict):
            rows = next((rows[k] for k in ('results', 'networks', 'scan_results')
                         if isinstance(rows.get(k), list)), None)
        if not isinstance(rows, list):
            raise SetupError('Unexpected scan response structure; see console.')
        return [row for row in rows if isinstance(row, dict) and isinstance(row.get('ssid'), str)]

    def provision(self, ssid, password, hidden=False, manual=None, rows=None, index=-1):
        if not ssid:
            raise SetupError('SSID is required.')
        self.console.remember(password)
        if hidden:
            if manual is None:
                raise SetupError('Hidden networks require explicit security numbers.')
            auth, cipher = map(security, manual)
        else:
            rows = self.scan() if rows is None else rows
            matches = [row for row in rows if row['ssid'] == ssid]
            if 0 <= index < len(rows) and rows[index]['ssid'] == ssid:
                selected = rows[index]
            elif not matches:
                raise SetupError('SSID not found by Chromecast. Scan again; no credentials submitted.')
            elif len({(security(r.get('wpa_auth')), security(r.get('wpa_cipher'))) for r in matches}) > 1:
                raise SetupError('Multiple security profiles; select the desired scan entry.')
            else:
                selected = matches[0]
            auth, cipher = security(selected.get('wpa_auth')), security(selected.get('wpa_cipher'))
        info = self.json('GET', '/setup/eureka_info')
        if not isinstance(info, dict):
            raise SetupError('Device information is not a JSON object.')
        key = load_key(info.get('public_key'))
        try:
            encrypted = base64.b64encode(key.encrypt(password.encode('utf-8'), padding.PKCS1v15())).decode('ascii')
        except ValueError as exc:
            raise SetupError('Password encryption failed for the supplied RSA key.') from exc
        self.console.remember(encrypted)
        payload = dict(ssid=ssid, wpa_auth=auth, wpa_cipher=cipher, enc_passwd=encrypted)
        if hidden:
            payload['hidden'] = True
        self.request('POST', '/setup/connect_wifi', payload)
        self.accepted = True
        self.request('POST', '/setup/save_wifi', {'keep_hotspot_until_connected': True})
        return 'Connect and save acknowledged. Check the Chromecast TV display for actual Wi-Fi status.'


class Worker(QObject):
    log = Signal(str)
    result = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, mode, url, options, sensitive):
        super().__init__()
        self.mode, self.url, self.options, self.sensitive = mode, url, options, sensitive

    @Slot()
    def run(self):
        client = None
        try:
            console = HttpConsole(self.log.emit, self.sensitive)
            console.write('OPERATION', f'{self.mode}; sensitive output={self.sensitive}')
            client = SetupClient(self.url, console)
            self.result.emit(client.scan() if self.mode == 'scan' else client.provision(**self.options))
        except Exception as exc:
            message = str(exc) if isinstance(exc, SetupError) else f'Unexpected {type(exc).__name__}'
            self.log.emit(message)
            self.error.emit(message)
        finally:
            if client is not None:
                client.close()
            self.finished.emit()


class ChromecastProvisioner(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Chromecast Gen 1 Provisioner — 1.0.4')
        self.resize(1000, 850)
        self.thread = None
        self.rows, self.rows_url = None, None
        layout = QVBoxLayout(self)
        split = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(split)
        controls = QWidget()
        form = QVBoxLayout(controls)
        form.addWidget(QLabel('Connect this PC to the Chromecast setup Wi-Fi before scanning.'))
        self.url_input = QLineEdit('http://192.168.255.249:8008')
        form.addWidget(QLabel('Chromecast setup URL:'))
        form.addWidget(self.url_input)
        form.addWidget(QLabel('Destination network (SSID):'))
        self.ssid_input = QComboBox()
        self.ssid_input.setEditable(True)
        self.ssid_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        form.addWidget(self.ssid_input)
        self.scan_button = QPushButton('Scan networks')
        self.scan_button.clicked.connect(lambda: self.start_job('scan', {}))
        form.addWidget(self.scan_button)
        row = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Wi-Fi password')
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(self.password_input)
        self.show_password_button = QPushButton('Show password')
        self.show_password_button.setCheckable(True)
        self.show_password_button.toggled.connect(self.toggle_password_visibility)
        row.addWidget(self.show_password_button)
        form.addLayout(row)
        self.hidden_checkbox = QCheckBox('Hidden network — explicit security values required')
        form.addWidget(self.hidden_checkbox)
        row = QHBoxLayout()
        self.auth_input, self.cipher_input = QLineEdit(), QLineEdit()
        self.auth_input.setPlaceholderText('wpa_auth (hidden only)')
        self.cipher_input.setPlaceholderText('wpa_cipher (hidden only)')
        for field in (self.auth_input, self.cipher_input):
            field.setEnabled(False)
            self.hidden_checkbox.toggled.connect(field.setEnabled)
            row.addWidget(field)
        form.addLayout(row)
        self.provision_button = QPushButton('Provision Device')
        self.provision_button.clicked.connect(self.setup_chromecast)
        form.addWidget(self.provision_button)
        self.status_label = QLabel('Ready')
        self.status_label.setWordWrap(True)
        form.addWidget(self.status_label)
        split.addWidget(controls)
        panel = QWidget()
        console_layout = QVBoxLayout(panel)
        console_layout.addWidget(QLabel('Communication console — prepared HTTP requests and received responses'))
        row = QHBoxLayout()
        self.sensitive_checkbox = QCheckBox('Show sensitive fields (unsafe to share)')
        self.sensitive_checkbox.toggled.connect(self.confirm_sensitive)
        row.addWidget(self.sensitive_checkbox)
        self.autoscroll = QCheckBox('Auto-scroll')
        self.autoscroll.setChecked(True)
        row.addWidget(self.autoscroll)
        for text, callback in [('Copy', self.copy_console), ('Save log...', self.save_console), ('Clear', self.clear_console)]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        console_layout.addLayout(row)
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.console.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        console_layout.addWidget(self.console)
        warning = QLabel('Default redaction is best-effort. Responses may contain SSIDs, MAC/IP addresses, '
                         'device IDs, or other private data. Review before sharing. '
                         'This is HTTP application logging, not a raw packet capture.')
        warning.setWordWrap(True)
        console_layout.addWidget(warning)
        split.addWidget(panel)
        split.setSizes([360, 450])

    def toggle_password_visibility(self, checked):
        self.password_input.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)
        self.show_password_button.setText('Hide password' if checked else 'Show password')

    def confirm_sensitive(self, checked):
        if checked:
            answer = QMessageBox.warning(self, 'Sensitive communication logging',
                'Full fields can expose credentials, tokens, and device details. '
                'Previously displayed lines are not changed when this option is disabled. Enable for future operations?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                self.sensitive_checkbox.setChecked(False)

    @Slot(str)
    def append_console(self, text):
        bar = self.console.verticalScrollBar()
        position = bar.value()
        self.console.appendPlainText(text)
        if self.autoscroll.isChecked():
            self.console.moveCursor(QTextCursor.MoveOperation.End)
        else:
            bar.setValue(position)

    def copy_console(self):
        QApplication.clipboard().setText(self.console.toPlainText())

    def save_console(self):
        name, _ = QFileDialog.getSaveFileName(self, 'Save console (review sensitive content first)',
                                             'chromecast_console.log', 'Log files (*.log);;All files (*)')
        if name:
            try:
                with open(name, 'w', encoding='utf-8') as stream:
                    stream.write(self.console.toPlainText())
            except OSError as exc:
                QMessageBox.warning(self, 'Save failed', str(exc))

    def clear_console(self):
        self.console.clear()

    def busy(self, state):
        for widget in (self.url_input, self.ssid_input, self.password_input,
                       self.scan_button, self.provision_button, self.hidden_checkbox,
                       self.sensitive_checkbox):
            widget.setEnabled(not state)
        for field in (self.auth_input, self.cipher_input):
            field.setEnabled(not state and self.hidden_checkbox.isChecked())

    def start_job(self, mode, options):
        if self.thread is not None:
            return
        self.active_url = self.url_input.text().strip().rstrip('/')
        self.busy(True)
        self.status_label.setText('Working...')
        self.thread = QThread(self)
        self.worker = Worker(mode, self.active_url, options, self.sensitive_checkbox.isChecked())
        self.worker.moveToThread(self.thread)
        self.worker.log.connect(self.append_console)
        self.worker.result.connect(self.handle_result)
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.job_finished)
        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def setup_chromecast(self):
        ssid = self.ssid_input.currentText()
        if not ssid:
            QMessageBox.warning(self, 'Missing SSID', 'Enter or select an SSID.')
            return
        hidden = self.hidden_checkbox.isChecked()
        manual = (self.auth_input.text(), self.cipher_input.text()) if hidden else None
        if hidden:
            try:
                for value in manual:
                    security(value)
            except SetupError as exc:
                QMessageBox.warning(self, 'Invalid security values', str(exc))
                return
        current_url = self.url_input.text().strip().rstrip('/')
        rows = self.rows if current_url == self.rows_url else None
        self.start_job('provision', dict(ssid=ssid, password=self.password_input.text(), hidden=hidden,
            manual=manual, rows=rows, index=self.ssid_input.currentIndex() if rows is not None else -1))

    @Slot(object)
    def handle_result(self, result):
        if isinstance(result, list):
            old = self.ssid_input.currentText()
            self.rows, self.rows_url = result, self.active_url
            self.ssid_input.clear()
            for row in result:
                self.ssid_input.addItem(row['ssid'])
                self.ssid_input.setItemData(self.ssid_input.count()-1,
                    f"wpa_auth={row.get('wpa_auth')}, wpa_cipher={row.get('wpa_cipher')}",
                    Qt.ItemDataRole.ToolTipRole)
            if old:
                self.ssid_input.setCurrentText(old)
            self.status_label.setText(f'Scan complete: {len(result)} entries.')
        else:
            self.status_label.setText(result)
            self.password_input.clear()
            self.show_password_button.setChecked(False)

    @Slot(str)
    def handle_error(self, message):
        self.status_label.setText(message)
        QMessageBox.warning(self, 'Chromecast setup', message)

    @Slot()
    def job_finished(self):
        self.thread, self.worker = None, None
        self.busy(False)

    def closeEvent(self, event):
        if self.thread is not None:
            QMessageBox.information(self, 'Busy', 'Wait for the current operation before closing.')
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = ChromecastProvisioner()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
