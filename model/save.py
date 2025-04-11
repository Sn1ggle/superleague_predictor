"""
save.py – Modell und Skalierer in Azure Blob Storage speichern
---------------------------------------------------------------
Dieses Skript lädt sowohl das persistierte ML-Modell (best_model.pkl) als auch den Skalierer (scaler.pkl)
und lädt beide in einen definierten Blobcontainer in Azure hoch. Der Connection-String wird aus der 
Umgebungsvariablen "AZURE_STORAGE_CONNECTION_STRING" gelesen.
Das Skript versieht die Blobnamen mit einer fortlaufenden Nummerierung basierend auf bereits vorhandenen
Modelldateien im Container.
"""

import os
import sys
import joblib
from azure.storage.blob import BlobServiceClient, ContainerClient
from datetime import datetime

# Lokale Dateinamen – passen Sie diese ggf. an
MODEL_FILENAME = "best_model.pkl"
SCALER_FILENAME = "scaler.pkl"
# Containername, in dem die Modelle und Skalierer abgelegt werden sollen
BLOB_CONTAINER_NAME = "models"

def get_blob_service_client():
    """Erstellt einen BlobServiceClient mithilfe des Connection-Strings aus der Umgebungsvariable."""
    connection_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_str:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING ist nicht gesetzt!")
    return BlobServiceClient.from_connection_string(connection_str)

def get_new_blob_name(container_client: ContainerClient, base_name: str) -> str:
    """
    Ermittelt einen neuen Blob-Namen mit fortlaufender Nummerierung.
    Sucht im Container nach vorhandenen Dateien, die dem Muster "base_name-<version>.pkl" folgen,
    und generiert einen neuen Namen.
    """
    blob_list = container_client.list_blobs(name_starts_with=base_name + "-")
    versions = []
    for blob in blob_list:
        try:
            version_str = blob.name.split("-")[-1].split(".")[0]
            versions.append(int(version_str))
        except (IndexError, ValueError):
            continue
    next_version = max(versions) + 1 if versions else 1
    return f"{base_name}-{next_version}.pkl"

def upload_file(filename, base_blob_name):
    """Lädt eine gegebene Datei in den Blob Storage hoch und verwendet fortlaufende Nummerierung."""
    if not os.path.exists(filename):
        print(f"Datei '{filename}' nicht gefunden. Bitte stellen Sie sicher, dass die Datei existiert.")
        sys.exit(1)
    
    blob_service_client = get_blob_service_client()
    # Container erstellen oder abrufen
    try:
        container_client = blob_service_client.create_container(BLOB_CONTAINER_NAME)
        print(f"Container '{BLOB_CONTAINER_NAME}' erstellt.")
    except Exception:
        container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)
    
    new_blob_name = get_new_blob_name(container_client, base_blob_name)
    print(f"Upload von {filename} als '{new_blob_name}'...")
    with open(filename, "rb") as data:
        container_client.upload_blob(new_blob_name, data)
    print(f"{filename} erfolgreich hochgeladen.")

def main():
    try:
        upload_file(MODEL_FILENAME, "model")
        upload_file(SCALER_FILENAME, "scaler")
    except Exception as e:
        print(f"Fehler beim Hochladen: {e}")

if __name__ == "__main__":
    main()
