import os
import getpass
from dotenv import load_dotenv
from icecream import ic
from pathlib import Path
def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"Set value for {var}: ")

def load_and_check_env(env_file: str = Path(".env_vars"), required_vars_file: str = Path("required_env_vars.txt")):
    current_dir = Path(__file__).parent
    root_dir = current_dir.parent
    env_file = root_dir / env_file
    required_vars_file = root_dir / required_vars_file
    print(f"Loading environment variables from {env_file}")
    load_dotenv(env_file)

    try:
        with open(required_vars_file) as f:
            required_vars = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        raise FileNotFoundError(f"{required_vars_file} not found.")

    # Prompt for missing variables
    for var in required_vars:
        _set_env(var)
