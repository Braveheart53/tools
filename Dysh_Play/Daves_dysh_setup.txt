#!/usr/bin/env python3
"""
Setup script for Dysh GUI
Installs dependencies and sets up the application
"""

import sys
import subprocess
import os
from pathlib import Path

def install_requirements():
    """Install required Python packages."""
    requirements = [
        "qtpy>=2.0.0",
        "pyside6>=6.0.0",
        "numpy>=1.20.0",
        "matplotlib>=3.5.0",
        "scipy>=1.7.0",
        "astropy>=5.0.0",
        "specutils>=1.7.0",
        "pandas>=1.3.0"
    ]

    print("Installing required packages...")
    for package in requirements:
        try:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ {package} installed successfully")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {package}")
            return False

    return True

def install_dysh():
    """Install Dysh package from GitHub."""
    try:
        print("Installing Dysh from GitHub...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "git+https://github.com/GreenBankObservatory/dysh.git"
        ])
        print("✓ Dysh installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install Dysh - GUI will work in mock mode")
        return False

def create_desktop_entry():
    """Create desktop entry for the application (Linux)."""
    if sys.platform != "linux":
        return

    desktop_entry = f"""[Desktop Entry]
Name=Dysh GUI
Comment=GBT IDL Style Interface for Spectral Line Analysis
Exec={sys.executable} {Path(__file__).parent / 'dysh_gui.py'}
Icon={Path(__file__).parent / 'icons' / 'dysh_icon.png'}
Terminal=false
Type=Application
Categories=Science;Astronomy;
"""

    try:
        desktop_path = Path.home() / ".local" / "share" / "applications" / "dysh-gui.desktop"
        desktop_path.parent.mkdir(parents=True, exist_ok=True)

        with open(desktop_path, 'w') as f:
            f.write(desktop_entry)

        os.chmod(desktop_path, 0o755)
        print(f"✓ Desktop entry created at {desktop_path}")

    except Exception as e:
        print(f"✗ Failed to create desktop entry: {e}")

def main():
    """Main setup function."""
    print("Dysh GUI Setup")
    print("=" * 50)

    # Check Python version
    if sys.version_info < (3.8):
        print("✗ Python 3.8 or higher required")
        return 1

    print(f"✓ Python {sys.version.split()[0]} detected")

    # Install requirements
    if not install_requirements():
        print("✗ Failed to install requirements")
        return 1

    # Try to install Dysh
    dysh_installed = install_dysh()

    # Create desktop entry (Linux only)
    create_desktop_entry()

    print("\n" + "=" * 50)
    print("Setup completed successfully!")

    if dysh_installed:
        print("\nDysh is fully installed and ready to use.")
    else:
        print("\nDysh installation failed - GUI will run in mock mode.")
        print("You can manually install Dysh later with:")
        print("pip install git+https://github.com/GreenBankObservatory/dysh.git")

    print("\nTo run the application:")
    print("python dysh_gui.py")

    print("\nFor help and documentation:")
    print("https://github.com/GreenBankObservatory/dysh")

    return 0

if __name__ == "__main__":
    sys.exit(main())
