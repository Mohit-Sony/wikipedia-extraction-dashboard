# backend/services/file_service.py
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self, wikipedia_data_dir: str = "../wikipedia_data"):
        self.data_dir = Path(wikipedia_data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
    # Add this method to FileService class

    def save_entity_data(self, qid: str, entity_type: str, data: Dict[str, Any]) -> bool:
        """Save entity data to JSON file in wikipedia_data directory"""
        try:
            # Get file path and ensure directory exists
            file_path = self.get_entity_file_path(qid, entity_type)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add extraction metadata
            data['extraction_metadata'] = {
                'timestamp': datetime.now().isoformat(),
                'pipeline_version': '2.0',
                'source': 'api_extraction'
            }
            
            # Save JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully saved entity {qid} to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save entity {qid}: {e}")
            return False

    def delete_entity_data(self, qid: str, entity_type: str) -> bool:
        """Delete entity data file"""
        try:
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
        """Check if entity file exists"""
        file_path = self.get_entity_file_path(qid, entity_type)
        return file_path.exists()

    def get_entity_file_path(self, qid: str, entity_type: str) -> Path:
        """Get the file path for an entity's JSON file"""
        type_dir = self.data_dir / entity_type.replace(' ', '_').replace('/', '_')
        return type_dir / f"{qid}.json"
    
    def read_entity_data(self, qid: str, entity_type: str) -> Optional[Dict[str, Any]]:
        """Read entity data from JSON file"""
        try:
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
        """Scan wikipedia_data directory and extract metadata from all JSON files"""
        entities = []
        
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
                            metadata = self._extract_metadata(entity_data, qid, entity_type, json_file)
                            entities.append(metadata)
                            
                    except Exception as e:
                        logger.error(f"Error processing {json_file}: {e}")
                        
        logger.info(f"Scanned {len(entities)} entities from wikipedia_data directory")
        return entities
    
    def _extract_metadata(self, data: Dict[str, Any], qid: str, entity_type: str, file_path: Path) -> Dict[str, Any]:
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
        
        return {
            'qid': qid,
            'title': data.get('title', ''),
            'type': entity_type,
            'short_desc': content.get('description') or content.get('extract', '')[:200] if content.get('extract') else None,
            'num_links': len(internal_links),
            'num_tables': len(tables),
            'num_images': len(images),
            'num_chunks': len(chunks),
            'page_length': metadata.get('page_length', 0),
            'extraction_date': extraction_date,
            'last_modified': last_modified,
            'file_path': str(file_path.relative_to(self.data_dir.parent)),
            'parent_qid': extraction_metadata.get('parent_qid'),
            'depth': extraction_metadata.get('depth', 0),
            'status': 'completed'  # Files in the directory are considered completed
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
        """Get statistics about the wikipedia_data directory"""
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