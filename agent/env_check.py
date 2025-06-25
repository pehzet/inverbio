import os
import getpass
from dotenv import load_dotenv

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"Set value for {var}: ")

def load_and_check_env(env_file: str = ".env_vars", required_vars_file: str = "required_env_vars.txt"):
    # Load environment variables from .env file
    load_dotenv(env_file)

    # Load required variables
    try:
        with open(required_vars_file) as f:
            required_vars = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        raise FileNotFoundError(f"{required_vars_file} not found.")

    # Prompt for missing variables
    for var in required_vars:
        _set_env(var)
