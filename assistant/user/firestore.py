
from typing import List, Dict
import firebase_admin
from firebase_admin import credentials, firestore

from datetime import datetime

from assistant.utils.firebase_utils import get_firestore_client

class UserFirestore:
    def __init__(self, data_source_name: str = None):
        self.db = get_firestore_client()

    def create_tables(self):
        """Firestore benötigt keine explizite Erstellung von Collections oder Tabellen."""
        print("Firestore collections are created implicitly when data is added.")
        return True

    def add_user_to_user_db(self, user_id: str, preferences=None) -> bool:
        """Add a user document."""
        try:
            if preferences is None:
                preferences = {}
            user_ref = self.db.collection('users').document(user_id)
            user_ref.set({
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'status': 'active',
                'preferences': preferences
            })
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False

    def get_user_information_from_user_db(self, user_id: str) -> Dict:
        """Get user document."""
        if user_id in ["anonymous", None]:
            return {"user_id": "anonymous", "preferences": {}}

        user_ref = self.db.collection('users').document(user_id)
        doc = user_ref.get()

        if doc.exists:
            user_data = doc.to_dict()
            return user_data
        else:
            print(f"User with ID {user_id} not found.")
            return {}

    def add_thread_to_user_db(self, thread_id: str, user_id: str) -> bool:
        """Add a thread document."""
        try:
            thread_ref = self.db.collection('threads').document(thread_id)
            thread_ref.set({
                'thread_id': thread_id,
                'title': 'New Thread',
                'description': 'New Thread',
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            })
            return True
        except Exception as e:
            print(f"Error adding thread: {e}")
            return False

    def update_thread_at_user_db(self, thread_id: str, field: str, value) -> bool:
        """Update a thread document."""
        try:
            if field not in {"user_id"}:
                raise ValueError("Invalid field name")

            thread_ref = self.db.collection('threads').document(thread_id)
            thread_ref.update({
                field: value,
                'updated_at': datetime.utcnow()
            })
            return True
        except Exception as e:
            print(f"Error updating thread: {e}")
            return False

    def get_threads_by_user_id(self, user_id: str) -> List[Dict]:
        """Get all threads for a user."""
        threads = self.db.collection('threads').where('user_id', '==', user_id).stream()
        threads_list = [thread.to_dict() for thread in threads]

        if not threads_list:
            print(f"No threads found for user with ID {user_id}.")
            return []
        return threads_list

    def get_thread_ids_by_user_id(self, user_id: str) -> List[str]:
        """Get thread ids for a user."""
        threads_list = self.get_threads_by_user_id(user_id)
        return [thread.get('thread_id') for thread in threads_list]