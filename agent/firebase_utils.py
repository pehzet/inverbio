from firebase_admin import credentials, firestore, storage as admin_storage
import firebase_admin

def initialize_firebase(
    project_id: str | None = None,
    credential_path: str | None = None,
    storage_bucket: str | None = None,
) -> None:
    """
    Initialize Firebase Admin SDK (Firestore + Storage) with optional project ID,
    credentials and default Storage-Bucket.
    """
    if not firebase_admin._apps:
        # Test
        storage_bucket ="inverbio-8342a.appspot.com" 
        # 1) Credentials wählen
        if credential_path:
            cred = credentials.Certificate(credential_path)
        else:
            cred = credentials.ApplicationDefault()
        # 2) Optionen für App
        app_opts: dict[str, str] = {}
        if project_id:
            app_opts["projectId"] = project_id
        if storage_bucket:
            app_opts["storageBucket"] = storage_bucket
        # 3) App initialisieren
        firebase_admin.initialize_app(cred, app_opts)

def get_firestore_client() -> firestore.Client:
    initialize_firebase()
    return firestore.client()

def get_storage_bucket():
    """
    Ruft den default Storage-Bucket ab, wie er in initialize_firebase
    per storage_bucket konfiguriert wurde.
    """
    initialize_firebase()
    return admin_storage.bucket()  # liest den storageBucket aus der App-Konfiguration
