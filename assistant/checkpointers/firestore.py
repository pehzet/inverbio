import os
import base64
import requests
from typing import Any
from urllib.parse import urlparse
from langchain.schema import HumanMessage, AIMessage
from langgraph_checkpoint_firestore.firestoreSaver import FirestoreSaver
from assistant.utils.firebase_utils import get_storage_bucket
from langgraph.checkpoint.base import CheckpointTuple
from icecream import ic
from typing import Optional
class FirebaseImageFirestoreSaver(FirestoreSaver):
    def __init__(
        self,
        *,
        project_id: str,
        checkpoints_collection: str | None,
        writes_collection: str,
        **kwargs
    ):
        super().__init__(
            project_id=project_id,
            checkpoints_collection=checkpoints_collection,
            writes_collection=writes_collection,
            **kwargs,
        )
        self._bucket = get_storage_bucket()

    def _upload_image(self, raw_bytes: bytes, dest_path: str, content_type: str) -> str:

        blob = self._bucket.blob(dest_path)
        blob.upload_from_string(raw_bytes, content_type=content_type)
        # make public instead of signed URL
        blob.make_public()
        url = blob.public_url
    
        return url

    def _download_image(self, public_url: str) -> bytes:
        # Use HTTP to fetch public URL
        resp = requests.get(public_url)
        resp.raise_for_status()
        return resp.content

    def _replace_data_urls(self, obj: Any, thread_id: str, checkpoint_id: str, counter_ref: dict):
        """
        Rekursive Hilfsfunktion: ersetzt alle data:* URLs in obj durch public URLs.
        counter_ref ist ein dict mit Schlüssel 'count', um den Zähler zu teilen.
        """
        # LangChain Messages
        if isinstance(obj, (HumanMessage, AIMessage)):
            for chunk in obj.content:
                self._replace_data_urls(chunk, thread_id, checkpoint_id, counter_ref)
            return

        # dict
        if isinstance(obj, dict):
            if obj.get('type') == 'image_url' and isinstance(obj.get('image_url'), dict):
                data_url = obj['image_url']['url']
                if data_url.startswith('data:') and ',' in data_url:
                    prefix, b64 = data_url.split(',', 1)
                    mime = prefix.split(':', 1)[1].split(';', 1)[0]
                    ext = mime.split('/', 1)[1]
                    raw = base64.b64decode(b64)
                    dest = f"{thread_id}/{checkpoint_id}/{counter_ref['count']}.{ext}"
                    public_url = self._upload_image(raw, dest, content_type=mime)
                    obj['image_url']['url'] = public_url
                    obj['image_url']['prefix'] = prefix
                    counter_ref['count'] += 1
                return
            # sonst recursiv
            for v in obj.values():
                self._replace_data_urls(v, thread_id, checkpoint_id, counter_ref)
            return

        # list
        if isinstance(obj, list):
            for item in obj:
                self._replace_data_urls(item, thread_id, checkpoint_id, counter_ref)

    def put(self, config: dict, checkpoint: dict, metadata: Any, new_versions) -> dict:
        thread_id = config['configurable']['thread_id']
        checkpoint_id = checkpoint['id']
        counter_ref = {'count': 0}
        self._replace_data_urls(metadata, thread_id, checkpoint_id, counter_ref)
        return super().put(config, checkpoint, metadata, new_versions)

    def put_writes(self, config: dict, writes: list[tuple[str, Any]], task_id: str) -> None:
        """
        Analog zu put: ersetzt alle data:* URLs in den Writes vor dem Speichern.
        """
        thread_id = config['configurable']['thread_id']
        checkpoint_ns = config['configurable'].get('checkpoint_ns')
        checkpoint_id = config['configurable'].get('checkpoint_id')
        counter_ref = {'count': 0}

        # writes ist List[Tuple[channel, value]]
        processed_writes: list[tuple[str, Any]] = []
        for channel, value in writes:
            self._replace_data_urls(value, thread_id, checkpoint_id, counter_ref)
            processed_writes.append((channel, value))

        super().put_writes(config, processed_writes, task_id)
    # def _restore_data_urls(self, obj: Any) -> None:
    #     """
    #     Rekursive Hilfsfunktion: ersetzt in obj alle public URLs zurück in data-URLs.
    #     """
    #     # 1) LangChain Messages auslassen, aber in deren content weitersuchen
    #     if isinstance(obj, (HumanMessage, AIMessage)):
    #         for chunk in obj.content:
    #             self._restore_data_urls(chunk)
    #         return

    #     # 2) dict: auf image_url prüfen, sonst rekursiv in alle Werte
    #     if isinstance(obj, dict):
    #         img = obj.get("image_url")
    #         if obj.get("type") == "image_url" and isinstance(img, dict):
    #             public_url = img["url"]
    #             prefix = img.get("prefix", "data:image/png;base64")
    #             # Bild herunterladen und base64-codieren
    #             raw = self._download_image(public_url)
    #             b64 = base64.b64encode(raw).decode("utf-8")
    #             # URL-Feld durch data-URL ersetzen
    #             img["url"] = f"{prefix},{b64}"
    #         else:
    #             for v in obj.values():
    #                 self._restore_data_urls(v)
    #         return

    #     # 3) list: in jedes Element reingehen
    #     if isinstance(obj, list):
    #         for item in obj:
    #             self._restore_data_urls(item)
    #         return
    # def get(self, config: dict, checkpoint_id: str) -> tuple:
    #     print(f"GET CALLED with id {checkpoint_id}!!!")
    #     data, versions = super().get(config, checkpoint_id)
    #     print("data", data)
    #     # rekonstruiere data URLS
    #     def recurse_restore(obj: Any):
    #         if isinstance(obj, (HumanMessage, AIMessage)):
    #             for chunk in obj.content:
    #                 recurse_restore(chunk)
    #             return
    #         if isinstance(obj, dict):
    #             if obj.get('type') == 'image_url' and isinstance(obj.get('image_url'), dict):
    #                 public_url = obj['image_url']['url']
    #                 prefix = obj['image_url'].get('prefix', 'data:image/png;base64')
    #                 raw = self._download_image(public_url)
    #                 b64 = base64.b64encode(raw).decode('utf-8')
    #                 obj['image_url']['url'] = f"{prefix},{b64}"
    #                 return
    #             for v in obj.values():
    #                 recurse_restore(v)
    #             return
    #         if isinstance(obj, list):
    #             for item in obj:
    #                 recurse_restore(item)
    #             return

    #     recurse_restore(data)

    #     return data, versions
    # def get_tuple(self, config: dict, **kwargs) -> CheckpointTuple | None:
    #     saved = super().get_tuple(config, **kwargs)
    #     if not saved:
    #         return None

    #     # saved ist ein NamedTuple mit den Feldern:
    #     #   .config, .checkpoint, .metadata, .parent_config, .pending_writes
    #     # Du kannst also so darauf zugreifen:

    #     checkpoint_dict = saved.checkpoint   # das Dict mit 'channel_values' etc.
     
    #     # Jetzt die Daten‐URLs wiederherstellen – z.B. in allen Channels:
    #     # wenn Dein Bild-JSON in checkpoint_dict['channel_values'] liegt:
    #     self._restore_data_urls(checkpoint_dict['channel_values'])
  
    #     # Und schließlich das unveränderte NamedTuple zurückgeben:
    #     return CheckpointTuple(
    #         config=saved.config,
    #         checkpoint=saved.checkpoint,
    #         metadata=saved.metadata,
    #         parent_config=saved.parent_config,
    #         pending_writes=saved.pending_writes
    #     )

def get_firestore_checkpoint(project_id: Optional[str]=None) -> FirebaseImageFirestoreSaver:
    project_id = "inverbio-8342a" if project_id is None else project_id # Default project ID for dev
    memory = FirebaseImageFirestoreSaver(project_id=project_id, checkpoints_collection='checkpoints', writes_collection='writes')
    return memory