import os
from typing import Literal, Union
from pathlib import Path

def check_setup(required_vars_file: str = None, required_vars: list[str] = None) -> None:
    check_if_env_vars_set(required_vars_file, required_vars)
    # env vars are needed for the following checks
    checks = [
        check_if_chroma_db_exists,
  
    ]
    for check in checks:
        if not check():
            raise RuntimeError(f"Setup check failed: {check.__name__}")
    print("All setup checks passed.")

def check_if_chroma_db_exists() -> bool:
    """
    Check if the Chroma vector store database exists.
    """
    chroma_dir = os.getenv("CHROMA_PRODUCT_DB")
    if not chroma_dir:
        return False
    if not Path(chroma_dir).exists():
        print(f"Chroma directory '{chroma_dir}' does not exist.")
        return False
    if not (Path(chroma_dir) / "chroma.sqlite3").exists():
        print(f"Chroma database file '{chroma_dir}/chroma.sqlite3' does not exist.")
        return False
    return True

def check_if_env_vars_set(required_vars_file: str = None, required_vars: list[str] = None) -> bool:
    """
    Check if all required environment variables are set.
    """
    if not required_vars and not required_vars_file:
        raise ValueError("Either 'required_vars' or 'required_vars_file' must be provided.")
    if required_vars_file:
        try:
            with open(required_vars_file) as f:
                required_vars = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except FileNotFoundError:
            raise FileNotFoundError(f"{required_vars_file} not found.")

    for var in required_vars:
        if not os.getenv(var):
            print(f"Environment variable '{var}' is not set.")
            return False
    return True



