import sqlite3
import json
from typing import List, Dict
def create_tables(db_path='user_db/user.db') -> bool:
    """Create the SQLite database and tables if they do not exist."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()



        # create users first for foreign key constraint
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            preferences TEXT  
        );
        """


        create_threads_table = """
        CREATE TABLE IF NOT EXISTS threads (
            thread_id TEXT PRIMARY KEY,
            user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """
        
        # Tabellen erstellen
        cursor.execute(create_users_table)
        cursor.execute(create_threads_table)

        conn.commit()
        conn.close()
        print("Tables created successfully.")
        return True
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")
        return False

def add_user_to_user_db(user_id:str, preferences=None, db_path='user_db/user.db') -> bool:
    """Add a user to the database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        if not preferences:
            preferences = json.dumps({})
        else:
            preferences = json.dumps(preferences, ensure_ascii=False)

        cursor.execute("INSERT INTO users (user_id, preferences) VALUES (?, ?)", (user_id, preferences))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error adding user: {e}")
        return False

def format_nested_dict(nested_dict: dict) -> Dict:
    def recurse(d):
        try:
            if isinstance(d, dict):
                loaded_d = d
            else:
                loaded_d = json.loads(d)
            for k, v in loaded_d.items():
                loaded_d[k] = recurse(v)
        except (json.JSONDecodeError, TypeError):
            return d
        return loaded_d


    nested_dict = recurse(nested_dict)
    return nested_dict

def get_user_from_user_db(user_id:str, db_path='user_db/user.db') -> Dict:
    """Load user from database"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # result as dictionary
    cursor = conn.cursor()
    
    # Benutzer abfragen
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if not user:
        print(f"User with ID {user_id} not found.")
        return {}
    user_dict = dict(user)
    user_dict = format_nested_dict(user_dict)
    return user_dict

def add_thread_to_user_db(thread_id, user_id) -> bool:
    """Add a thread for a user to the database"""
    try:
        conn = sqlite3.connect('user_db/user.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO threads (thread_id, user_id) VALUES (?, ?)", (thread_id, user_id))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error adding thread: {e}")
        return False
def update_thread_at_user_db(thread_id, field, value) -> bool:
    """Update a thread in the database and set updated_at to current timestamp
    Returns the updated thread as a dictionary."""
    try:
        conn = sqlite3.connect('user_db/user.db')
        cursor = conn.cursor()

        # Dynamisches Field einfügen ist potenziell riskant (SQL Injection),
        # daher sicherstellen, dass field ein gültiger Spaltenname ist.
        if field not in {"user_id"}:  # Erweitere das Set mit erlaubten Feldern
            raise ValueError("Invalid field name")

        cursor.execute(
            f"""
            UPDATE threads
            SET {field} = ?, updated_at = CURRENT_TIMESTAMP
            WHERE thread_id = ?
            """,
            (value, thread_id)
        )

        conn.commit()
        conn.close()

        return True
    except (sqlite3.Error, ValueError) as e:
        print(f"Error updating thread: {e}")
        return False


def get_threads_by_user_id(user_id:str) -> List:
    """Load threads for a user from database"""
    conn = sqlite3.connect('user_db/user.db')
    conn.row_factory = sqlite3.Row  # result as dictionary
    cursor = conn.cursor()
    
    # Benutzer abfragen
    cursor.execute("SELECT * FROM threads WHERE user_id = ?", (user_id,))
    threads = cursor.fetchall()
    conn.close()
    if not threads:
        print(f"No threads found for user with ID {user_id}.")
        return []
    threads_list = [dict(thread) for thread in threads]
    return threads_list



if __name__ == "__main__":
    create_tables()
    user_id = "00001"
    import json
    with open("user_preferences.json", "r", encoding="utf-8") as f:
        preferences = json.load(f)
    print(preferences)
    add_user_to_user_db(user_id, preferences)
    user = get_user_from_user_db(user_id)
    print(user)
