import os
from typing import Literal, Union
from pathlib import Path
from dotenv import load_dotenv
import traceback
BASE_DIR = Path(__file__).parent
os.environ["BASE_DIR"] = str(BASE_DIR)
def setup_all():
    env_var_path = Path("assistant/.env_vars")
    req_env_var_path = Path("assistant/required_env_vars.txt")
    load_dotenv(str(env_var_path))
    check_if_env_vars_set(required_vars_file=str(req_env_var_path))
    print("Environment variables are set. Proceeding with setup...")
    setup_barcode_db()
    setup_user_db("postgres")
    setup_product_db("chroma")
    setup_checkpoint_db("postgres")
    print("Setup completed successfully.")

def setup_product_dbs():
    env_var_path = Path("assistant/.env_vars")
    req_env_var_path = Path("assistant/required_env_vars.txt")
    load_dotenv(str(env_var_path))
    check_if_env_vars_set(required_vars_file=str(req_env_var_path))
    print("Environment variables are set. Proceeding with product associated setup...")
    setup_product_db("chroma")
    setup_barcode_db()
def setup_user_db(db_type: Literal["sqlite","mysql","postgres"] = "postgres") -> None:
    """Set up the user database based on the specified type.
    Args:
        db_type (Literal["sqlite", "mysql", "postgres"]): The type of database to set up.
    """
    if db_type == "sqlite":
        raise NotImplementedError("SQLite setup is not implemented yet.")
    elif db_type == "mysql":
        raise NotImplementedError("MySQL setup is not implemented yet.")
    elif db_type == "postgres":
        from assistant.user.database import setup_user_db as _setup_user_db, get_data_source_from_env
        data_source = get_data_source_from_env("postgres")
        if _setup_user_db(type="postgres", data_source_name=data_source):
            print("PostgreSQL user database setup completed.")
        else:
            print("ERROR: Failed to set up PostgreSQL user database.")
def setup_product_db(
    db_type: Literal["chroma"] = "chroma",
    ) -> None:
    """Set up the product database based on the specified type.
    Args:
        db_type (Literal["chroma"]): The type of database to set up.
    """
    if db_type == "chroma":
        from assistant.rag.setup import setup_product_db_chroma
        if setup_product_db_chroma():
            print("Chroma product database setup completed.")
        else:
            print("ERROR: Failed to set up Chroma product database.")

def setup_checkpoint_db(
    db_type: Literal["sqlite","mysql","postgres"] = "postgres",
    ) -> None:
    if db_type == "sqlite":
        raise NotImplementedError("SQLite setup is not implemented yet.")
    elif db_type == "mysql":
        raise NotImplementedError("MySQL setup is not implemented yet.")
    elif db_type == "postgres":
        from assistant.checkpointers.postgres import setup_postgres_saver
        if setup_postgres_saver():
            print("PostgreSQL checkpoint database setup completed.")
        else:
            print("ERROR: Failed to set up PostgreSQL checkpoint database.")
    else:
        raise ValueError(f"Unsupported checkpoint database type: {db_type}")

def setup_barcode_db():
    """
    Set up the barcode database.
    This function checks if the barcode database exists and sets it up if not.
    """
    from barcode.barcode import setup_product_db_sqlite
    try:
        setup_product_db_sqlite()
        print("Barcode database setup completed successfully.")
    except Exception as e:
        print(f"ERROR: Failed to set up barcode database: {e}")
        traceback.print_exc()

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
    BASE_DIR = os.environ.get("BASE_DIR", Path(__file__).parent)
    BASE_DIR = Path(BASE_DIR).resolve()
    chroma_dir = os.getenv("CHROMA_PRODUCT_DB")
    chroma_dir = BASE_DIR / chroma_dir if chroma_dir else BASE_DIR / "chroma_products"
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




if __name__ == "__main__":
    # py setup_assistant.py all/products
    try:
        import sys
        if len(sys.argv) > 1:
            if sys.argv[1] == "all":
                setup_all()
            elif sys.argv[1] == "products":
                setup_product_dbs()
            else:
                print(f"Unknown argument: {sys.argv[1]}")
    except Exception as e:
        print(f"Setup failed: {e}")
        traceback.print_exc()
        exit(1)
    print("Setup completed successfully.")