#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chromecast Gen 1 direct provisioner, version 1.0.3.
Original author: William W. Wallace, Adaptive Electrodynamics LLC.
Dependencies: qtpy, PySide6, requests, cryptography.
Connect the PC to the Chromecast setup hotspot before running this file.
Protocol references:
https://gist.github.com/interfect/5f68381d55658d334e2bc4619d796476
https://github.com/rithvikvibhu/GHLocalApi/issues/88
No claim of hardware validation. HTTP acceptance is not Wi-Fi verification.
"""
import os
import sys
import time
import base64
import binascii
import requests
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_der_public_key
from cryptography.hazmat.primitives.asymmetric import padding, rsa

os.environ['QT_API'] = 'pyside6'
from qtpy.QtCore import QObject, QThread, Signal, Slot
from qtpy.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, QPlainTextEdit,
    QMessageBox)


class SetupError(Exception):
    """A sanitized, user-facing provisioning failure."""


def load_chromecast_public_key(value):
    if not isinstance(value, (str, bytes)):
        raise SetupError('Device public_key is missing or is not text.')
    try:
        text = value.decode('ascii') if isinstance(value, bytes) else value
        text = text.strip().replace('\\r\\n', '\n').replace('\\n', '\n')
        if text.startswith('-----BEGIN '):
            key = load_pem_public_key(text.encode('ascii'))
        else:
            compact = ''.join(text.split())
            if not compact:
                raise ValueError('empty key')
            compact += '=' * (-len(compact) % 4)
            key = load_der_public_key(base64.b64decode(compact, validate=True))
    except (ValueError, UnicodeError, binascii.Error) as exc:
        raise SetupError('Device public_key is neither valid PEM nor Base64 DER.') from exc
    if not isinstance(key, rsa.RSAPublicKey):
        raise SetupError('Device public_key is not an RSA public key.')
    return key


def normalize_scan_results(data):
    if isinstance(data, dict):
        data = next((data[k] for k in ('results', 'networks', 'scan_results')
                     if isinstance(data.get(k), list)), None)
    if not isinstance(data, list):
        raise SetupError('Unrecognized scan response: expected a list of networks.')
    return [row for row in data if isinstance(row, dict) and isinstance(row.get('ssid'), str)]


def security_value(value, field):
    if isinstance(value, bool):
        raise SetupError(f'{field} must be a non-negative integer from the device scan.')
    try:
        number = int(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise SetupError(f'{field} is missing or is not an integer.') from exc
    if number < 0 or (isinstance(value, float) and value != number):
        raise SetupError(f'{field} must be a non-negative integer.')
    return number


def choose_network(rows, ssid, index=None):
    matches = [row for row in rows if row['ssid'] == ssid]
    if index is not None and 0 <= index < len(rows) and rows[index]['ssid'] == ssid:
        return rows[index]
    if not matches:
        raise SetupError('SSID not found by the Chromecast. Scan again or use hidden-network '
                         'mode with explicit authentication/cipher values. No credentials sent.')
    security = {(security_value(row.get('wpa_auth'), 'wpa_auth'),
                 security_value(row.get('wpa_cipher'), 'wpa_cipher')) for row in matches}
    if len(security) > 1:
        raise SetupError('This SSID has multiple security configurations. Use Scan networks '
                         'and select the desired entry in the list.')
    return matches[0]


class SetupClient:
    def __init__(self, base_url, report=None, session=None, sleep=time.sleep):
        if not base_url.startswith('http://'):
            raise SetupError('This build uses the original HTTP setup service. '
                             'Use http://192.168.255.249:8008 unless the device IP differs.')
        self.base_url = base_url.rstrip('/')
        self.report = report or (lambda message: None)
        self.session = session if session is not None else requests.Session()
        self.session.trust_env = False  # Do not route the local setup through environment proxies.
        self.session.headers.update({'User-Agent': 'curl/7.68.0', 'Accept': 'application/json'})
        self.sleep = sleep
        self.connect_accepted = False

    def close(self):
        self.session.close()

    def request(self, method, endpoint, payload=None):
        self.report(f'{method} {endpoint}')
        kwargs = {'timeout': (5, 15), 'allow_redirects': False}
        if payload is not None:
            kwargs['json'] = payload
        try:
            response = self.session.request(method, self.base_url + endpoint, **kwargs)
        except requests.RequestException as exc:
            suffix = (' Connection was accepted earlier, but saving is unconfirmed. '
                      'Check the TV before retrying.' if self.connect_accepted else
                      ' If this was connect_wifi, the device may have switched networks '
                      'before replying; check the TV before retrying.')
            raise SetupError(f'{method} {endpoint}: {type(exc).__name__}.{suffix}') from exc
        self.report(f'{endpoint}: HTTP {response.status_code}; response bytes={len(response.content)}')
        if not 200 <= response.status_code < 300:
            suffix = (' Connection was accepted, but saving failed.' if self.connect_accepted else
                      ' The device did not confirm acceptance; save_wifi was not called.')
            raise SetupError(f'{method} {endpoint} returned HTTP {response.status_code}.{suffix} '
                             'HTTP 500 does not by itself identify a wrong endpoint or a bad password. '
                             'No automatic retry was performed.')
        return response

    def json_response(self, response, endpoint):
        try:
            return response.json()
        except ValueError as exc:
            raise SetupError(f'{endpoint} did not return valid JSON.') from exc

    def scan(self):
        self.request('POST', '/setup/scan_wifi', {})
        self.report('Waiting 12 seconds for the device Wi-Fi scan...')
        self.sleep(12)
        response = self.request('GET', '/setup/scan_results')
        rows = normalize_scan_results(self.json_response(response, '/setup/scan_results'))
        self.report(f'Scan returned {len(rows)} entries. Security numbers are device-reported.')
        return rows

    def provision(self, ssid, password, hidden=False, rows=None, index=None, manual=None):
        if not ssid:
            raise SetupError('Network name is required.')
        if hidden:
            if manual is None:
                raise SetupError('Hidden networks require explicit auth/cipher values; this tool '
                                 'does not guess numeric security codes.')
            auth = security_value(manual[0], 'wpa_auth')
            cipher = security_value(manual[1], 'wpa_cipher')
        else:
            rows = rows if rows is not None else self.scan()
            selected = choose_network(rows, ssid, index)
            auth = security_value(selected.get('wpa_auth'), 'wpa_auth')
            cipher = security_value(selected.get('wpa_cipher'), 'wpa_cipher')
        self.report(f'Using wpa_auth={auth}, wpa_cipher={cipher}.')
        response = self.request('GET', '/setup/eureka_info')
        info = self.json_response(response, '/setup/eureka_info')
        if not isinstance(info, dict):
            raise SetupError('eureka_info response is not a JSON object.')
        key = load_chromecast_public_key(info.get('public_key'))
        try:
            encrypted = key.encrypt(password.encode('utf-8'), padding.PKCS1v15())
        except ValueError as exc:
            raise SetupError('Password cannot be encrypted with the returned RSA key.') from exc
        payload = {'ssid': ssid, 'wpa_auth': auth, 'wpa_cipher': cipher,
                   'enc_passwd': base64.b64encode(encrypted).decode('ascii')}
        if hidden:
            payload['hidden'] = True
        # Do not retry a credential submission: a dropped connection may mean a network change.
        self.request('POST', '/setup/connect_wifi', payload)
        self.connect_accepted = True
        # This call must follow connect immediately, before the setup hotspot disappears.
        self.request('POST', '/setup/save_wifi', {'keep_hotspot_until_connected': True})
        self.report('Connect and save requests accepted. Wi-Fi association is not independently verified.')
        return 'Settings submitted and save acknowledged. Check the Chromecast TV display.'


class Worker(QObject):
    log = Signal(str)
    result = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, mode, base_url, options):
        super().__init__()
        self.mode, self.base_url, self.options = mode, base_url, options

    @Slot()
    def run(self):
        client = None
        try:
            client = SetupClient(self.base_url, self.log.emit)
            result = client.scan() if self.mode == 'scan' else client.provision(**self.options)
            self.result.emit(result)
        except Exception as exc:
            self.error.emit(str(exc) if isinstance(exc, SetupError) else
                            f'Unexpected error: {type(exc).__name__}. No automatic retry performed.')
        finally:
            if client is not None:
                client.close()
            self.finished.emit()


class ChromecastProvisioner(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Chromecast Gen 1 Provisioner — 1.0.3')
        self.resize(620, 590)
        self.rows = None
        self.rows_url = None
        self.thread = None
        layout = QVBoxLayout(self)
        note = QLabel('Connect this PC to the Chromecast setup Wi-Fi first.\n'
                      'Scan networks, select your destination SSID, then provision.')
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addWidget(QLabel('Chromecast setup URL (HTTP service):'))
        self.url_input = QLineEdit('http://192.168.255.249:8008')
        layout.addWidget(self.url_input)
        layout.addWidget(QLabel('Network Name (SSID) — select a scan entry or type the exact name:'))
        self.ssid_input = QComboBox()
        self.ssid_input.setEditable(True)
        self.ssid_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        layout.addWidget(self.ssid_input)
        self.scan_button = QPushButton('Scan networks')
        self.scan_button.clicked.connect(self.scan_networks)
        layout.addWidget(self.scan_button)
        layout.addWidget(QLabel('Wi-Fi password:'))
        row = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(self.password_input)
        self.show_password_button = QPushButton('Show password')
        self.show_password_button.setCheckable(True)
        self.show_password_button.toggled.connect(self.toggle_password_visibility)
        row.addWidget(self.show_password_button)
        layout.addLayout(row)
        self.hidden_checkbox = QCheckBox('Hidden network (requires explicit security values below)')
        layout.addWidget(self.hidden_checkbox)
        row = QHBoxLayout()
        self.auth_input = QLineEdit()
        self.auth_input.setPlaceholderText('wpa_auth — hidden mode only')
        self.cipher_input = QLineEdit()
        self.cipher_input.setPlaceholderText('wpa_cipher — hidden mode only')
        row.addWidget(self.auth_input)
        row.addWidget(self.cipher_input)
        layout.addLayout(row)
        self.auth_input.setEnabled(False)
        self.cipher_input.setEnabled(False)
        self.hidden_checkbox.toggled.connect(self.auth_input.setEnabled)
        self.hidden_checkbox.toggled.connect(self.cipher_input.setEnabled)
        self.provision_button = QPushButton('Provision Device')
        self.provision_button.clicked.connect(self.setup_chromecast)
        layout.addWidget(self.provision_button)
        self.status_label = QLabel('Ready')
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText('Diagnostics exclude passwords, encrypted credentials, and response bodies.')
        layout.addWidget(self.log_output)

    def toggle_password_visibility(self, checked):
        self.password_input.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)
        self.show_password_button.setText('Hide password' if checked else 'Show password')

    def set_busy(self, busy):
        for widget in (self.scan_button, self.provision_button, self.url_input,
                       self.ssid_input, self.password_input, self.hidden_checkbox):
            widget.setEnabled(not busy)
        self.auth_input.setEnabled(not busy and self.hidden_checkbox.isChecked())
        self.cipher_input.setEnabled(not busy and self.hidden_checkbox.isChecked())

    def start_job(self, mode, options):
        if self.thread is not None:
            return
        base_url = self.url_input.text().strip().rstrip('/')
        self.set_busy(True)
        self.status_label.setText('Scanning...' if mode == 'scan' else 'Provisioning...')
        self.status_label.setStyleSheet('')
        self.log_output.clear()
        self.thread = QThread(self)
        self.worker = Worker(mode, base_url, options)
        self.worker.moveToThread(self.thread)
        self.worker.log.connect(self.log_output.appendPlainText)
        self.worker.result.connect(self.handle_result)
        self.worker.error.connect(self.handle_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.job_finished)
        self.thread.started.connect(self.worker.run)
        self.active_url = base_url
        self.thread.start()

    def scan_networks(self):
        self.start_job('scan', {})

    def setup_chromecast(self):
        ssid = self.ssid_input.currentText()
        if not ssid:
            QMessageBox.warning(self, 'Missing SSID', 'Enter or select the network name.')
            return
        hidden = self.hidden_checkbox.isChecked()
        manual = (self.auth_input.text(), self.cipher_input.text()) if hidden else None
        if hidden:
            try:
                for value, field in zip(manual, ('wpa_auth', 'wpa_cipher')):
                    security_value(value, field)
            except SetupError as exc:
                QMessageBox.warning(self, 'Security values required', str(exc))
                return
        current_url = self.url_input.text().strip().rstrip('/')
        rows = self.rows if self.rows_url == current_url else None
        index = self.ssid_input.currentIndex() if rows is not None else None
        self.start_job('provision', dict(ssid=ssid, password=self.password_input.text(),
                       hidden=hidden, rows=rows, index=index, manual=manual))

    @Slot(object)
    def handle_result(self, result):
        if isinstance(result, list):
            old = self.ssid_input.currentText()
            self.rows = result
            self.rows_url = self.active_url
            self.ssid_input.clear()
            for row in result:
                self.ssid_input.addItem(row['ssid'])
                index = self.ssid_input.count() - 1
                from qtpy.QtCore import Qt
                self.ssid_input.setItemData(index,
                    f"wpa_auth={row.get('wpa_auth')}, wpa_cipher={row.get('wpa_cipher')}",
                    Qt.ItemDataRole.ToolTipRole)
            if old:
                self.ssid_input.setCurrentText(old)
            self.status_label.setText(f'Scan complete: {len(result)} entries. Select your SSID.')
        else:
            self.status_label.setText(result)
            self.status_label.setStyleSheet('color: green;')
            self.password_input.clear()
            self.show_password_button.setChecked(False)

    @Slot(str)
    def handle_error(self, message):
        self.status_label.setText('Request failed or result unconfirmed. See diagnostics.')
        self.status_label.setStyleSheet('color: red;')
        self.log_output.appendPlainText(message)
        QMessageBox.warning(self, 'Chromecast setup', message)

    @Slot()
    def job_finished(self):
        self.thread = None
        self.worker = None
        self.set_busy(False)

    def closeEvent(self, event):
        if self.thread is not None:
            QMessageBox.information(self, 'Operation in progress',
                                    'Wait for the current operation to finish before closing.')
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
