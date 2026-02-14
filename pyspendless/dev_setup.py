import os
import subprocess

VENV_DIR = ".venv"
REQUIREMENTS = "requirements.txt"
ENV_EXAMPLE = ".env.example"
ENV_FILE = ".env"


def run(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def main():
    if not os.path.exists(VENV_DIR):
        run(f"python3 -m venv {VENV_DIR}")
    run(f"source {VENV_DIR}/bin/activate && pip install -U pip")
    run(f"source {VENV_DIR}/bin/activate && pip install -r {REQUIREMENTS}")
    if os.path.exists(ENV_EXAMPLE) and not os.path.exists(ENV_FILE):
        run(f"cp {ENV_EXAMPLE} {ENV_FILE}")
    print("Setup completato. Per attivare l'ambiente: source .venv/bin/activate")
    print("Per avviare il server: flask run oppure python -m app")

if __name__ == "__main__":
    main()
