# backend/services/google_drive_service.py
import os
import io
import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveService:
    """Service for managing files in Google Drive"""

    def __init__(self, credentials_path: str = None, root_folder_name: str = "wikipedia_data"):
        """
        Initialize Google Drive service

        Args:
            credentials_path: Path to credentials.json file
            root_folder_name: Name of root folder in Google Drive for storing data
        """
        if credentials_path is None:
            # Default to credentials.json in project root
            credentials_path = os.path.join(
                os.path.dirname(__file__),
                "../../credentials.json"
            )

        self.credentials_path = credentials_path
        self.root_folder_name = root_folder_name
        self.service = None
        self.root_folder_id = None
        self._folder_cache = {}  # Cache folder IDs by name

        # Initialize the service
        self._authenticate()
        self._ensure_root_folder()

    def _authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        token_path = os.path.join(os.path.dirname(self.credentials_path), "token.json")

        # Token file stores user's access and refresh tokens
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Google Drive authentication successful")

    def _ensure_root_folder(self):
        """Ensure root folder exists in Google Drive"""
        try:
            # Search for existing root folder
            query = f"name='{self.root_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = results.get('files', [])

            if files:
                self.root_folder_id = files[0]['id']
                logger.info(f"Found existing root folder: {self.root_folder_name} (ID: {self.root_folder_id})")
            else:
                # Create root folder
                file_metadata = {
                    'name': self.root_folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = self.service.files().create(
                    body=file_metadata,
                    fields='id'
                ).execute()
                self.root_folder_id = folder.get('id')
                logger.info(f"Created root folder: {self.root_folder_name} (ID: {self.root_folder_id})")

        except HttpError as error:
            logger.error(f"Error ensuring root folder: {error}")
            raise

    def _get_or_create_folder(self, folder_name: str, parent_id: str = None) -> str:
        """Get or create a folder in Google Drive"""
        if parent_id is None:
            parent_id = self.root_folder_id

        # Check cache
        cache_key = f"{parent_id}/{folder_name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        try:
            # Search for existing folder
            query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = results.get('files', [])

            if files:
                folder_id = files[0]['id']
            else:
                # Create folder
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_id]
                }
                folder = self.service.files().create(
                    body=file_metadata,
                    fields='id'
                ).execute()
                folder_id = folder.get('id')
                logger.info(f"Created folder: {folder_name} (ID: {folder_id})")

            # Cache the result
            self._folder_cache[cache_key] = folder_id
            return folder_id

        except HttpError as error:
            logger.error(f"Error getting/creating folder {folder_name}: {error}")
            raise

    def upload_file(self, file_name: str, content: str, folder_name: str = None) -> Optional[str]:
        """
        Upload a file to Google Drive

        Args:
            file_name: Name of the file (e.g., "Q123.json")
            content: File content as string
            folder_name: Folder name (entity type), if None uploads to root

        Returns:
            File ID if successful, None otherwise
        """
        try:
            # Get or create folder
            if folder_name:
                parent_id = self._get_or_create_folder(folder_name)
            else:
                parent_id = self.root_folder_id

            # Check if file already exists
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)'
            ).execute()

            existing_files = results.get('files', [])

            # Prepare file content
            fh = io.BytesIO(content.encode('utf-8'))
            media = MediaIoBaseUpload(fh, mimetype='application/json', resumable=True)

            if existing_files:
                # Update existing file
                file_id = existing_files[0]['id']
                file = self.service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                logger.info(f"Updated file: {file_name} in folder {folder_name}")
            else:
                # Create new file
                file_metadata = {
                    'name': file_name,
                    'parents': [parent_id]
                }
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                logger.info(f"Uploaded new file: {file_name} to folder {folder_name}")

            return file.get('id')

        except HttpError as error:
            logger.error(f"Error uploading file {file_name}: {error}")
            return None

    def download_file(self, file_name: str, folder_name: str = None) -> Optional[str]:
        """
        Download a file from Google Drive

        Args:
            file_name: Name of the file (e.g., "Q123.json")
            folder_name: Folder name (entity type), if None searches in root

        Returns:
            File content as string if successful, None otherwise
        """
        try:
            # Get folder ID
            if folder_name:
                parent_id = self._get_or_create_folder(folder_name)
            else:
                parent_id = self.root_folder_id

            # Search for file
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)'
            ).execute()

            files = results.get('files', [])

            if not files:
                logger.warning(f"File not found: {file_name} in folder {folder_name}")
                return None

            file_id = files[0]['id']

            # Download file content
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()

            content = fh.getvalue().decode('utf-8')
            return content

        except HttpError as error:
            logger.error(f"Error downloading file {file_name}: {error}")
            return None

    def delete_file(self, file_name: str, folder_name: str = None) -> bool:
        """
        Delete a file from Google Drive

        Args:
            file_name: Name of the file (e.g., "Q123.json")
            folder_name: Folder name (entity type), if None searches in root

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get folder ID
            if folder_name:
                parent_id = self._get_or_create_folder(folder_name)
            else:
                parent_id = self.root_folder_id

            # Search for file
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)'
            ).execute()

            files = results.get('files', [])

            if not files:
                logger.warning(f"File not found: {file_name} in folder {folder_name}")
                return False

            file_id = files[0]['id']

            # Delete file
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file: {file_name} from folder {folder_name}")
            return True

        except HttpError as error:
            logger.error(f"Error deleting file {file_name}: {error}")
            return False

    def file_exists(self, file_name: str, folder_name: str = None) -> bool:
        """
        Check if a file exists in Google Drive

        Args:
            file_name: Name of the file (e.g., "Q123.json")
            folder_name: Folder name (entity type), if None searches in root

        Returns:
            True if file exists, False otherwise
        """
        try:
            # Get folder ID
            if folder_name:
                parent_id = self._get_or_create_folder(folder_name)
            else:
                parent_id = self.root_folder_id

            # Search for file
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)'
            ).execute()

            files = results.get('files', [])
            return len(files) > 0

        except HttpError as error:
            logger.error(f"Error checking file existence {file_name}: {error}")
            return False

    def list_all_files(self) -> List[Dict[str, Any]]:
        """
        List all JSON files in the root folder and subfolders

        Returns:
            List of file metadata dictionaries
        """
        all_files = []

        try:
            # Get all folders in root
            query = f"'{self.root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            folders = results.get('files', [])

            # For each folder, list JSON files
            for folder in folders:
                folder_name = folder['name']
                folder_id = folder['id']

                # List JSON files in this folder
                file_query = f"'{folder_id}' in parents and name contains '.json' and trashed=false"
                file_results = self.service.files().list(
                    q=file_query,
                    spaces='drive',
                    fields='files(id, name, size, modifiedTime)',
                    pageSize=1000
                ).execute()

                files = file_results.get('files', [])

                for file in files:
                    all_files.append({
                        'folder_name': folder_name,
                        'file_name': file['name'],
                        'file_id': file['id'],
                        'size': int(file.get('size', 0)),
                        'modified_time': file.get('modifiedTime')
                    })

            logger.info(f"Listed {len(all_files)} files from Google Drive")
            return all_files

        except HttpError as error:
            logger.error(f"Error listing files: {error}")
            return []

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics

        Returns:
            Dictionary with storage stats
        """
        try:
            files = self.list_all_files()

            # Group by folder
            entities_by_type = {}
            total_size = 0

            for file in files:
                folder_name = file['folder_name']
                if folder_name not in entities_by_type:
                    entities_by_type[folder_name] = 0
                entities_by_type[folder_name] += 1
                total_size += file.get('size', 0)

            return {
                'total_entities': len(files),
                'entities_by_type': entities_by_type,
                'total_size_mb': total_size / (1024 * 1024)  # Convert to MB
            }

        except Exception as error:
            logger.error(f"Error getting storage stats: {error}")
            return {
                'total_entities': 0,
                'entities_by_type': {},
                'total_size_mb': 0
            }
