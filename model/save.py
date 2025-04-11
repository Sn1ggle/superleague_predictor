"""
save.py – Modell in Azure Blob Storage speichern
---------------------------------------------------
Dieses Skript lädt das persistierte ML-Modell (best_model.pkl) und lädt es in einen definierten Blobcontainer in Azure hoch.
Der Connection-String wird aus der Umgebungsvariablen "AZURE_STORAGE_CONNECTION_STRING" gelesen.
Das Skript versieht den Blobnamen mit einer fortlaufenden Nummerierung (Versionierung) basierend auf bereits bestehenden
Modellen im Container.
"""

import os
import sys
import joblib
from azure.storage.blob import BlobServiceClient, ContainerClient
from datetime import datetime

# Definiere den lokalen Pfad zum Modell (anpassen, falls benötigt)
MODEL_FILENAME = "best_model.pkl"
# Der Containername, in dem die Modelle abgelegt werden sollen
BLOB_CONTAINER_NAME = "models"

def get_blob_service_client():
    """Erstellt einen BlobServiceClient mithilfe des Connection-Strings aus der Umgebungsvariable."""

    connection_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_str:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING ist nicht gesetzt!")
    return BlobServiceClient.from_connection_string(connection_str)

def get_new_blob_name(container_client: ContainerClient) -> str:
    """
    Ermittelt einen neuen Blob-Namen mit fortlaufender Nummerierung.
    Sucht im Container nach vorhandenen Modelldateien, die dem Muster "model-<version>.pkl" folgen,
    und generiert einen neuen Namen.
    """
    blob_list = container_client.list_blobs(name_starts_with="model-")
    versions = []
    for blob in blob_list:
        try:
            # Extrahiere die Versionsnummer aus dem Blob-Namen
            version_str = blob.name.split("-")[-1].split(".")[0]
            versions.append(int(version_str))
        except (IndexError, ValueError):
            continue
    next_version = max(versions) + 1 if versions else 1
    new_blob_name = f"model-{next_version}.pkl"
    return new_blob_name

def upload_model():
    """Lädt das Modell in den Azure Blob Storage hoch."""
    # Prüfe, ob die Modell-Datei existiert
    if not os.path.exists(MODEL_FILENAME):
        print(f"Modell-Datei '{MODEL_FILENAME}' nicht gefunden. Bitte stellen Sie sicher, dass das Modell existiert.")
        sys.exit(1)
    
    blob_service_client = get_blob_service_client()
    
    # Erstelle den Container, falls er noch nicht existiert
    try:
        container_client = blob_service_client.create_container(BLOB_CONTAINER_NAME)
        print(f"Container '{BLOB_CONTAINER_NAME}' erstellt.")
    except Exception:
        container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)
    
    # Generiere einen neuen Blob-Namen für das Modell
    new_blob_name = get_new_blob_name(container_client)
    
    print(f"Upload des Modells als '{new_blob_name}'...")
    # Öffne die Modell-Datei und lade sie hoch
    with open(MODEL_FILENAME, "rb") as data:
        container_client.upload_blob(new_blob_name, data)
    
    print("Modell erfolgreich hochgeladen.")

if __name__ == "__main__":
    try:
        upload_model()
    except Exception as e:
        print(f"Fehler beim Hochladen des Modells: {e}")
