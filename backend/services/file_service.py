# backend/services/file_service.py
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from services.google_drive_service import GoogleDriveService

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self, use_google_drive: bool = True, credentials_path: str = None):
        """
        Initialize FileService with Google Drive or local storage

        Args:
            use_google_drive: If True, use Google Drive; if False, use local storage
            credentials_path: Path to Google Drive credentials.json
        """
        self.use_google_drive = use_google_drive

        if self.use_google_drive:
            # Initialize Google Drive service
            self.drive_service = GoogleDriveService(credentials_path=credentials_path)
            logger.info("FileService initialized with Google Drive storage")
        else:
            # Fallback to local storage (for development/testing)
            self.data_dir = Path("../wikipedia_data")
            self.data_dir.mkdir(exist_ok=True)
            logger.info("FileService initialized with local storage")
        
    # Add this method to FileService class

    def save_entity_data(self, qid: str, entity_type: str, data: Dict[str, Any]) -> bool:
        """Save entity data to JSON file in Google Drive or local storage"""
        try:
            # Add extraction metadata
            data['extraction_metadata'] = {
                'timestamp': datetime.now().isoformat(),
                'pipeline_version': '2.0',
                'source': 'api_extraction'
            }

            # Convert to JSON string
            json_content = json.dumps(data, indent=2, ensure_ascii=False)

            if self.use_google_drive:
                # Save to Google Drive
                folder_name = entity_type.replace(' ', '_').replace('/', '_')
                file_name = f"{qid}.json"
                file_id = self.drive_service.upload_file(file_name, json_content, folder_name)

                if file_id:
                    logger.info(f"Successfully saved entity {qid} to Google Drive folder {folder_name}")
                    return True
                else:
                    logger.error(f"Failed to save entity {qid} to Google Drive")
                    return False
            else:
                # Save to local storage
                file_path = self.get_entity_file_path(qid, entity_type)
                file_path.parent.mkdir(parents=True, exist_ok=True)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_content)

                logger.info(f"Successfully saved entity {qid} to {file_path}")
                return True

        except Exception as e:
            logger.error(f"Failed to save entity {qid}: {e}")
            return False

    def delete_entity_data(self, qid: str, entity_type: str) -> bool:
        """Delete entity data file from Google Drive or local storage"""
        try:
            if self.use_google_drive:
                # Delete from Google Drive
                folder_name = entity_type.replace(' ', '_').replace('/', '_')
                file_name = f"{qid}.json"
                success = self.drive_service.delete_file(file_name, folder_name)

                if success:
                    logger.info(f"Deleted entity file: {qid} from Google Drive folder {folder_name}")
                return success
            else:
                # Delete from local storage
                file_path = self.get_entity_file_path(qid, entity_type)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted entity file: {file_path}")
                    return True
                return False

        except Exception as e:
            logger.error(f"Failed to delete entity {qid}: {e}")
            return False

    def entity_file_exists(self, qid: str, entity_type: str) -> bool:
        """Check if entity file exists in Google Drive or local storage"""
        if self.use_google_drive:
            folder_name = entity_type.replace(' ', '_').replace('/', '_')
            file_name = f"{qid}.json"
            return self.drive_service.file_exists(file_name, folder_name)
        else:
            file_path = self.get_entity_file_path(qid, entity_type)
            return file_path.exists()

    def get_entity_file_path(self, qid: str, entity_type: str) -> Path:
        """Get the file path for an entity's JSON file (local storage only)"""
        if not self.use_google_drive:
            type_dir = self.data_dir / entity_type.replace(' ', '_').replace('/', '_')
            return type_dir / f"{qid}.json"
        else:
            # Return a virtual path for compatibility
            return Path(f"wikipedia_data/{entity_type}/{qid}.json")

    def read_entity_data(self, qid: str, entity_type: str) -> Optional[Dict[str, Any]]:
        """Read entity data from JSON file in Google Drive or local storage"""
        try:
            if self.use_google_drive:
                # Read from Google Drive
                folder_name = entity_type.replace(' ', '_').replace('/', '_')
                file_name = f"{qid}.json"
                content = self.drive_service.download_file(file_name, folder_name)

                if content:
                    return json.loads(content)
                else:
                    logger.warning(f"Entity file not found in Google Drive: {qid}")
                    return None
            else:
                # Read from local storage
                file_path = self.get_entity_file_path(qid, entity_type)
                if not file_path.exists():
                    logger.warning(f"Entity file not found: {file_path}")
                    return None

                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)

        except Exception as e:
            logger.error(f"Error reading entity {qid}: {e}")
            return None
    
    def scan_wikipedia_data_directory(self) -> List[Dict[str, Any]]:
        """Scan wikipedia_data directory (Google Drive or local) and extract metadata from all JSON files"""
        entities = []

        if self.use_google_drive:
            # Scan Google Drive
            logger.info("Scanning Google Drive for entity files...")
            files = self.drive_service.list_all_files()

            for file_info in files:
                try:
                    folder_name = file_info['folder_name']
                    file_name = file_info['file_name']

                    if file_name.startswith("Q") and file_name.endswith(".json"):
                        qid = file_name.replace('.json', '')
                        entity_type = folder_name

                        # Read entity data
                        entity_data = self.read_entity_data(qid, entity_type)

                        if entity_data:
                            # Create virtual file path for metadata
                            virtual_path = Path(f"wikipedia_data/{entity_type}/{file_name}")
                            metadata = self._extract_metadata_from_drive(
                                entity_data, qid, entity_type, file_info
                            )
                            entities.append(metadata)

                except Exception as e:
                    logger.error(f"Error processing Google Drive file {file_info.get('file_name')}: {e}")

            logger.info(f"Scanned {len(entities)} entities from Google Drive")

        else:
            # Scan local storage
            for type_dir in self.data_dir.iterdir():
                if not type_dir.is_dir():
                    continue

                entity_type = type_dir.name
                logger.info(f"Scanning {entity_type} directory...")

                for json_file in type_dir.glob("*.json"):
                    if json_file.name.startswith("Q") and json_file.name.endswith(".json"):
                        try:
                            qid = json_file.stem
                            entity_data = self.read_entity_data(qid, entity_type)

                            if entity_data:
                                metadata = self._extract_metadata_local(entity_data, qid, entity_type, json_file)
                                entities.append(metadata)

                        except Exception as e:
                            logger.error(f"Error processing {json_file}: {e}")

            logger.info(f"Scanned {len(entities)} entities from local storage")

        return entities
    
    def _extract_metadata_from_drive(self, data: Dict[str, Any], qid: str, entity_type: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from entity JSON data stored in Google Drive"""
        # Parse modification time
        from datetime import datetime
        try:
            file_modified = datetime.fromisoformat(file_info['modified_time'].replace('Z', '+00:00'))
        except:
            file_modified = datetime.now()

        # Extract data from JSON structure
        content = data.get('content', {})
        links = data.get('links', {})
        internal_links = links.get('internal_links', [])
        tables = data.get('tables', [])
        images = data.get('images', [])
        chunks = data.get('chunks', [])
        metadata = data.get('metadata', {})
        extraction_metadata = data.get('extraction_metadata', {})

        # Parse extraction date
        extraction_date = None
        if extraction_metadata.get('timestamp'):
            try:
                extraction_date = datetime.fromisoformat(extraction_metadata['timestamp'].replace('Z', '+00:00'))
            except:
                extraction_date = file_modified

        # Parse last modified
        last_modified = None
        if metadata.get('last_modified'):
            try:
                last_modified = datetime.fromisoformat(metadata['last_modified'].replace('Z', '+00:00'))
            except:
                pass

        # Calculate counts
        num_links = len(internal_links)
        num_tables = len(tables)
        num_images = len(images)
        num_chunks = len(chunks)
        page_length = metadata.get('page_length', 0)

        # Validate extraction
        if num_links == 0 and num_tables == 0 and num_images == 0 and num_chunks == 0 and page_length == 0:
            status = 'failed'
            logger.warning(f"Entity {qid} has empty extraction data (all counts are 0)")
        elif num_chunks == 0 and page_length == 0:
            status = 'failed'
            logger.warning(f"Entity {qid} has no content (no chunks or page length)")
        else:
            status = 'completed'

        return {
            'qid': qid,
            'title': data.get('title', ''),
            'type': entity_type,
            'short_desc': content.get('description') or content.get('extract', '')[:200] if content.get('extract') else None,
            'num_links': num_links,
            'num_tables': num_tables,
            'num_images': num_images,
            'num_chunks': num_chunks,
            'page_length': page_length,
            'extraction_date': extraction_date,
            'last_modified': last_modified,
            'file_path': f"wikipedia_data/{entity_type}/{qid}.json",
            'parent_qid': extraction_metadata.get('parent_qid'),
            'depth': extraction_metadata.get('depth', 0),
            'status': status
        }

    def _extract_metadata_local(self, data: Dict[str, Any], qid: str, entity_type: str, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from entity JSON data"""
        # Get file stats
        stat = file_path.stat()
        file_modified = datetime.fromtimestamp(stat.st_mtime)

        # Extract data from JSON structure
        content = data.get('content', {})
        links = data.get('links', {})
        internal_links = links.get('internal_links', [])
        tables = data.get('tables', [])
        images = data.get('images', [])
        chunks = data.get('chunks', [])
        metadata = data.get('metadata', {})
        extraction_metadata = data.get('extraction_metadata', {})

        # Parse extraction date
        extraction_date = None
        if extraction_metadata.get('timestamp'):
            try:
                extraction_date = datetime.fromisoformat(extraction_metadata['timestamp'].replace('Z', '+00:00'))
            except:
                extraction_date = file_modified

        # Parse last modified
        last_modified = None
        if metadata.get('last_modified'):
            try:
                last_modified = datetime.fromisoformat(metadata['last_modified'].replace('Z', '+00:00'))
            except:
                pass

        # Calculate counts
        num_links = len(internal_links)
        num_tables = len(tables)
        num_images = len(images)
        num_chunks = len(chunks)
        page_length = metadata.get('page_length', 0)

        # Validate if extraction has meaningful data
        # If all counts are 0, the extraction likely failed or returned empty data
        if num_links == 0 and num_tables == 0 and num_images == 0 and num_chunks == 0 and page_length == 0:
            status = 'failed'
            logger.warning(f"Entity {qid} has empty extraction data (all counts are 0)")
        elif num_chunks == 0 and page_length == 0:
            # No content at all - definitely failed
            status = 'failed'
            logger.warning(f"Entity {qid} has no content (no chunks or page length)")
        else:
            status = 'completed'

        return {
            'qid': qid,
            'title': data.get('title', ''),
            'type': entity_type,
            'short_desc': content.get('description') or content.get('extract', '')[:200] if content.get('extract') else None,
            'num_links': num_links,
            'num_tables': num_tables,
            'num_images': num_images,
            'num_chunks': num_chunks,
            'page_length': page_length,
            'extraction_date': extraction_date,
            'last_modified': last_modified,
            'file_path': str(file_path.relative_to(self.data_dir.parent)),
            'parent_qid': extraction_metadata.get('parent_qid'),
            'depth': extraction_metadata.get('depth', 0),
            'status': status
        }
    
    def get_entity_preview(self, qid: str, entity_type: str) -> Optional[Dict[str, Any]]:
        """Get entity preview data for the dashboard"""
        entity_data = self.read_entity_data(qid, entity_type)
        if not entity_data:
            return None
        
        # Create a preview with limited data to avoid large payloads
        preview = {
            'qid': qid,
            'title': entity_data.get('title', ''),
            'type': entity_type,
            'content': {
                'extract': entity_data.get('content', {}).get('extract', '')[:500],
                'description': entity_data.get('content', {}).get('description', ''),
                'summary': entity_data.get('content', {}).get('summary', '')[:300]
            },
            'infobox': entity_data.get('infobox', {}),
            'links': {
                'internal_count': len(entity_data.get('links', {}).get('internal_links', [])),
                'external_count': len(entity_data.get('links', {}).get('external_links', [])),
                'sample_internal': entity_data.get('links', {}).get('internal_links', [])[:5]
            },
            'metadata': {
                'page_length': entity_data.get('metadata', {}).get('page_length', 0),
                'last_modified': entity_data.get('metadata', {}).get('last_modified'),
                'num_tables': len(entity_data.get('tables', [])),
                'num_images': len(entity_data.get('images', [])),
                'num_chunks': len(entity_data.get('chunks', []))
            }
        }
        
        return preview
    
    def get_entity_relationships(self, qid: str, entity_type: str) -> List[Dict[str, Any]]:
        """Get related entities for network visualization"""
        entity_data = self.read_entity_data(qid, entity_type)
        if not entity_data:
            return []
        
        relationships = []
        internal_links = entity_data.get('links', {}).get('internal_links', [])
        
        for link in internal_links[:20]:  # Limit to avoid overwhelming the UI
            relationships.append({
                'source': qid,
                'target': link.get('qid', ''),
                'title': link.get('title', ''),
                'type': link.get('type', 'unknown'),
                'description': link.get('shortDesc', '')
            })
        
        return relationships
    
    def get_directory_stats(self) -> Dict[str, Any]:
        """Get statistics about the wikipedia_data directory (Google Drive or local)"""
        if self.use_google_drive:
            # Get stats from Google Drive
            return self.drive_service.get_storage_stats()
        else:
            # Get stats from local storage
            stats = {
                'total_entities': 0,
                'entities_by_type': {},
                'total_size_mb': 0
            }

            for type_dir in self.data_dir.iterdir():
                if not type_dir.is_dir():
                    continue

                entity_type = type_dir.name
                json_files = list(type_dir.glob("Q*.json"))
                count = len(json_files)

                stats['entities_by_type'][entity_type] = count
                stats['total_entities'] += count

                # Calculate directory size
                size = sum(f.stat().st_size for f in json_files) / (1024 * 1024)  # MB
                stats['total_size_mb'] += size

            return stats