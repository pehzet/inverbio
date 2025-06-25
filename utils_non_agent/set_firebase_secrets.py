import os
import subprocess
from pathlib import Path
from dotenv import dotenv_values

# Stelle sicher, dass python-dotenv installiert ist:
# pip install python-dotenv

# Pfad zur .env-Datei
def set_firebase_secrets(env_path: str = '.env'):

    # Stelle sicher, dass python-dotenv installiert ist:
    # pip install python-dotenv

    # Pfad zur .env-Datei
    # env_path = Path('.') / '.env'

    if not os.path.exists(env_path):
        print("❌ .env-Datei nicht gefunden!")
        exit(1)

    # Lade Variablen aus der .env-Datei
    env_vars = dotenv_values(env_path)
    print(env_vars)
    # Setze jede Variable als Secret in Firebase
    for key, value in env_vars.items():
        if not key or not value:
            continue

        print(f"🔐 Setze Secret: {key}")
        try:
            subprocess.run(
                ['firebase', 'functions:secrets:set', key, '--data', value],
                check=True
            )
        except Exception as e:
            print(f"❌ Fehler beim Setzen von {key}: {e}")

if __name__ == "__main__":


    # Rufe die Funktion auf
    set_firebase_secrets(".env_vars")
