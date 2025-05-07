from firebase_admin import credentials, firestore
import firebase_admin

def initialize_firestore(project_id: str = None, credential_path: str = None) -> None:
    """
    Initialize Firestore client with optional project ID and credentials.

    Args:
        project_id (str): Optional GCP project ID.
        credential_path (str): Optional path to service account key file.
    """
    # Initialize Firebase Admin SDK if not already initialized  
    if not firebase_admin._apps:
        if credential_path:
            cred = credentials.Certificate(credential_path)
        else:
            cred = credentials.ApplicationDefault()

        app_args = {}
        if project_id:
            app_args["projectId"] = project_id

        firebase_admin.initialize_app(cred, app_args)

def get_firestore_client() -> firestore.Client:
    """
    Get Firestore client.

    Returns:
        firestore.Client: Firestore client instance.
    """
    initialize_firestore()
    return firestore.client()