# from typing import Any, Dict
# import firebase_admin
# from firebase_admin import credentials, firestore
# from langgraph.checkpoint.base import BaseCheckpointSaver
# from langgraph.checkpoint.memory import InMemorySaver
# from firebase_utils import initialize_firestore, get_firestore_client
# ims = InMemorySaver()
# class FirestoreCheckpointSaver(BaseCheckpointSaver):
#     """
#     A Firestore-based checkpoint saver for LangGraph using firebase_admin SDK.
#     Stores and retrieves pipeline state dictionaries in Google Firestore.
#     """
#     def __init__(
#         self,
#         project_id: str = None,
#         credential_path: str = None,
#         collection_name: str = "langgraph_checkpoints"
#     ) -> None:

#         self.collection = self.db.collection(collection_name)

#     def save_checkpoint(self, key: str, state: Dict[str, Any]) -> None:
#         """
#         Save the given state dict under the specified key.

#         Args:
#             key: Unique identifier for this checkpoint (e.g., run ID).
#             state: Serializable dictionary representing pipeline state.
#         """
#         doc_ref = self.collection.document(key)
#         doc_ref.set({"state": state})

#     def load_checkpoint(self, key: str) -> Dict[str, Any]:
#         """
#         Load and return the state dict for the specified key.

#         Args:
#             key: Unique identifier for the checkpoint to load.

#         Returns:
#             The state dict if found, otherwise an empty dict.
#         """
#         doc_ref = self.collection.document(key)
#         snapshot = doc_ref.get()
#         if snapshot.exists:
#             data = snapshot.to_dict()
#             return data.get("state", {})
#         return {}

#     def delete_checkpoint(self, key: str) -> None:
#         """
#         Remove the checkpoint associated with the given key.

#         Args:
#             key: Unique identifier for the checkpoint to delete.
#         """
#         doc_ref = self.collection.document(key)
#         doc_ref.delete()

# if __name__ == "__main__":
#     # Beispiel zur Verwendung des FirestoreCheckpointSaver
    # initialize_firestore()
    # saver = FirestoreCheckpointSaver()
from langgraph_checkpoint_firestore import FirestoreSaver
saver = FirestoreSaver(project_id=None, checkpoints_collection='langchain', writes_collection='langchain_writes')
