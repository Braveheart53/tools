#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# %% chromecast_setup_qt.py Info
=============================================================================
Chromecast Gen 1 (H2G2-42) Direct Provisioner
=============================================================================

A GUI application to provision a 1st Gen Google Chromecast (H2G2-42)
by communicating directly with its local REST API over the setup Wi-Fi network.
Bypasses the deprecated Google Home discovery flow by extracting the device 
RSA public key and securely transmitting WPA2 credentials.

# %%% Author Info
@Author: William W. Wallace — Adaptive Electrodynamics LLC
Email  : wwallace@electrodynamics.us
Product: Chromecast Direct Provisioner — Publisher: Adaptive Electrodynamics LLC
Date   : 2026-10-24
Python : 3.12
Version: 1.0.0
Deps   : qtpy, pyside6, requests, cryptography

# %%% Usage
-----
Connect your Wi-Fi interface to the open `ChromecastXXXX.b` setup network, 
then run:
    python chromecast_setup_qt.py
"""

import sys
import os
import requests
import base64

# Enforce the use of PySide6 as the backend for the qtpy abstraction layer.
# This must be set before importing qtpy modules.
os.environ["QT_API"] = "pyside6"

from qtpy.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel,
                            QLineEdit, QCheckBox, QPushButton, QMessageBox)
from qtpy.QtCore import Qt
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

class ChromecastProvisioner(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initializes the layout, widgets, and window properties."""
        self.setWindowTitle("Chromecast Gen 1 Provisioner")
        self.resize(380, 280)

        # Use a vertical box layout to stack widgets vertically
        layout = QVBoxLayout()

        # --- SSID Input Field ---
        self.ssid_label = QLabel("Network Name (SSID):")
        self.ssid_label.setStyleSheet("font-weight: bold;")
        self.ssid_input = QLineEdit()
        layout.addWidget(self.ssid_label)
        layout.addWidget(self.ssid_input)

        # --- Password Input Field ---
        self.password_label = QLabel("WPA2 Password:")
        self.password_label.setStyleSheet("font-weight: bold;")
        self.password_input = QLineEdit()
        # Mask the password characters for security
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)

        # --- Hidden Network Toggle ---
        # Maps to the 'hidden' boolean in the final JSON payload
        self.hidden_checkbox = QCheckBox("Network is Hidden")
        layout.addWidget(self.hidden_checkbox)

        # --- Execution Button ---
        self.provision_button = QPushButton("Provision Device")
        self.provision_button.setStyleSheet(
            "background-color: #005a9e; color: white; font-weight: bold; padding: 8px; margin-top: 10px;"
        )
        # Bind the button click event to the provisioning method
        self.provision_button.clicked.connect(self.setup_chromecast)
        layout.addWidget(self.provision_button)

        # --- Status Indicator ---
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: gray; margin-top: 10px;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def setup_chromecast(self):
        """
        Executes the three-step provisioning workflow:
        1. Fetch the Chromecast's RSA public key.
        2. Encrypt the user's Wi-Fi password.
        3. Post the credentials to bypass the Google Home app.
        """
        # Retrieve and sanitize user inputs from the GUI
        ssid = self.ssid_input.text().strip()
        password = self.password_input.text()
        is_hidden = self.hidden_checkbox.isChecked()

        # Validate that the SSID is not blank
        if not ssid:
            QMessageBox.warning(self, "Input Error", "Network Name (SSID) is required.")
            return

        # Explicitly spoof the User-Agent as curl. 
        # The Chromecast HTTP daemon (eureka) will return a 404 Not Found if it detects standard python-requests headers.
        headers = {"User-Agent": "curl/7.68.0", "Content-Type": "application/json"}
        
        # The static IP address of the Chromecast while broadcasting its setup network
        base_url = "http://192.168.255.249:8008"

        try:
            # Update GUI status
            self.status_label.setText("Fetching public key from Chromecast...")
            self.status_label.setStyleSheet("color: blue;")
            QApplication.processEvents() # Force GUI to refresh before blocking network calls

            # STEP 1: Fetch the public key from the device diagnostics endpoint
            info_resp = requests.get(f"{base_url}/setup/eureka_info", headers=headers, timeout=5)
            info_resp.raise_for_status() # Raise an exception if the HTTP request fails
            public_key_pem = info_resp.json().get("public_key")

            if not public_key_pem:
                raise ValueError("Public key not found in the eureka_info response.")

            # Update GUI status
            self.status_label.setText("Encrypting password...")
            QApplication.processEvents()

            # STEP 2: Encrypt the Wi-Fi password
            # Load the raw PEM string into a cryptographic object using the cryptography library
            public_key = load_pem_public_key(public_key_pem.encode('utf-8'), backend=default_backend())
            
            # Encrypt the plaintext password using RSA with PKCS#1 v1.5 padding (expected by Eureka firmware)
            encrypted_password = public_key.encrypt(
                password.encode('utf-8'),
                padding.PKCS1v15()
            )
            
            # Convert the raw encrypted bytes to a Base64 string for JSON transmission
            enc_passwd_b64 = base64.b64encode(encrypted_password).decode('utf-8')

            # STEP 3: Construct the configuration payload
            # wpa_auth = 3 translates to WPA2-PSK
            # wpa_cipher = 2 translates to AES encryption
            payload = {
                "ssid": ssid,
                "wpa_auth": 3,
                "wpa_cipher": 2,
                "enc_passwd": enc_passwd_b64,
                "hidden": is_hidden
            }

            # Update GUI status
            self.status_label.setText("Transmitting network credentials...")
            QApplication.processEvents()

            # Post the encrypted credentials to the connection endpoint
            connect_resp = requests.post(f"{base_url}/setup/connect_wifi", json=payload, headers=headers, timeout=5)
            connect_resp.raise_for_status()

            # Handle successful deployment
            self.status_label.setText("Success! Watch the Chromecast LED.")