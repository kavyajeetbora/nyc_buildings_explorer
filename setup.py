import os
import sys
import subprocess
import shutil
import argparse

VENV_DIR = "venv"
REQUIREMENTS_FILE = "requirements.txt"

def create_venv():
    """Create a virtual environment and install requirements."""
    if os.path.exists(VENV_DIR):
        print(f"Virtual environment '{VENV_DIR}' already exists.")
    else:
        print(f"Creating virtual environment in '{VENV_DIR}'...")
        subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])
    pip_path = os.path.join(VENV_DIR, "Scripts", "pip.exe") if os.name == "nt" else os.path.join(VENV_DIR, "bin", "pip")
    print(f"Installing packages from {REQUIREMENTS_FILE}...")
    subprocess.check_call([pip_path, "install", "-r", REQUIREMENTS_FILE])
    print("Setup complete.")


def clear_venv():
    """Delete the virtual environment folder."""
    if os.path.exists(VENV_DIR):
        print(f"Removing virtual environment '{VENV_DIR}'...")
        shutil.rmtree(VENV_DIR)
        print("Virtual environment removed.")
    else:
        print(f"No virtual environment found at '{VENV_DIR}'.")


def main():
    parser = argparse.ArgumentParser(description="Setup or clear Python venv.")
    parser.add_argument("action", choices=["setup", "clear"], help="Action to perform: setup or clear the venv.")
    args = parser.parse_args()
    if args.action == "setup":
        create_venv()
    elif args.action == "clear":
        clear_venv()

if __name__ == "__main__":
    main()
