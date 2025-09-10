# backend/services/sync_service.py
from sqlalchemy.orm import Session
from database.models import Entity, QueueEntry
from services.file_service import FileService
from utils.schemas import QueueType, EntityStatus
from typing import List, Dict, Any
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self, file_service: FileService):
        self.file_service = file_service
        
    def sync_database_with_files(self, db: Session) -> Dict[str, int]:
        """Sync database with files in wikipedia_data directory"""
        logger.info("Starting database sync with files...")
        
        # Get all entities from files
        file_entities = self.file_service.scan_wikipedia_data_directory()
        
        # Get existing entities from database
        existing_qids = set(entity.qid for entity in db.query(Entity.qid).all())
        
        stats = {
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        for entity_data in file_entities:
            try:
                qid = entity_data['qid']
                
                if qid in existing_qids:
                    # Update existing entity
                    if self._update_entity_from_file(db, entity_data):
                        stats['updated'] += 1
                    else:
                        stats['skipped'] += 1
                else:
                    # Add new entity
                    if self._create_entity_from_file(db, entity_data):
                        stats['added'] += 1
                        existing_qids.add(qid)
                    else:
                        stats['errors'] += 1
                        
            except Exception as e:
                logger.error(f"Error syncing entity {entity_data.get('qid', 'unknown')}: {e}")
                stats['errors'] += 1
        
        db.commit()
        logger.info(f"Sync completed: {stats}")
        return stats
    
    def _create_entity_from_file(self, db: Session, entity_data: Dict[str, Any]) -> bool:
        """Create new entity in database from file data"""
        try:
            entity = Entity(
                qid=entity_data['qid'],
                title=entity_data['title'],
                type=entity_data['type'],
                short_desc=entity_data.get('short_desc'),
                num_links=entity_data.get('num_links', 0),
                num_tables=entity_data.get('num_tables', 0),
                num_images=entity_data.get('num_images', 0),
                num_chunks=entity_data.get('num_chunks', 0),
                page_length=entity_data.get('page_length', 0),
                extraction_date=entity_data.get('extraction_date'),
                last_modified=entity_data.get('last_modified'),
                file_path=entity_data['file_path'],
                status=entity_data.get('status', 'completed'),
                parent_qid=entity_data.get('parent_qid'),
                depth=entity_data.get('depth', 0)
            )
            
            db.add(entity)
            
            # Add to completed queue
            queue_entry = QueueEntry(
                qid=entity_data['qid'],
                queue_type=QueueType.COMPLETED,
                added_by="sync_service",
                processed_date=entity_data.get('extraction_date', datetime.utcnow())
            )
            
            db.add(queue_entry)
            return True
            
        except Exception as e:
            logger.error(f"Error creating entity {entity_data['qid']}: {e}")
            return False
    
    def _update_entity_from_file(self, db: Session, entity_data: Dict[str, Any]) -> bool:
        """Update existing entity in database from file data"""
        try:
            entity = db.query(Entity).filter(Entity.qid == entity_data['qid']).first()
            if not entity:
                return False
            
            # Update fields that might have changed
            entity.title = entity_data['title']
            entity.short_desc = entity_data.get('short_desc')
            entity.num_links = entity_data.get('num_links', 0)
            entity.num_tables = entity_data.get('num_tables', 0)
            entity.num_images = entity_data.get('num_images', 0)
            entity.num_chunks = entity_data.get('num_chunks', 0)
            entity.page_length = entity_data.get('page_length', 0)
            entity.last_modified = entity_data.get('last_modified')
            entity.updated_at = datetime.utcnow()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating entity {entity_data['qid']}: {e}")
            return False
    
    def add_entity_from_extraction(self, db: Session, entity_data: Dict[str, Any]) -> bool:
        """Add entity to database when it's newly extracted"""
        try:
            # Check if entity already exists
            existing = db.query(Entity).filter(Entity.qid == entity_data['qid']).first()
            if existing:
                logger.info(f"Entity {entity_data['qid']} already exists, updating...")
                return self._update_entity_from_file(db, entity_data)
            
            # Create new entity
            success = self._create_entity_from_file(db, entity_data)
            if success:
                db.commit()
                logger.info(f"Added new entity {entity_data['qid']} to database")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding entity from extraction {entity_data.get('qid')}: {e}")
            db.rollback()
            return False
    
    def get_entities_for_queue_population(self, db: Session, entity_data: Dict[str, Any]) -> List[str]:
        """Extract linked entities that should be added to queues"""
        try:
            # Read the full entity data from file
            full_data = self.file_service.read_entity_data(
                entity_data['qid'], 
                entity_data['type']
            )
            
            if not full_data:
                return []
            
            linked_qids = []
            internal_links = full_data.get('links', {}).get('internal_links', [])
            
            for link in internal_links:
                link_qid = link.get('qid')
                if link_qid:
                    # Check if this entity already exists in database
                    existing = db.query(Entity).filter(Entity.qid == link_qid).first()
                    if not existing:
                        linked_qids.append({
                            'qid': link_qid,
                            'title': link.get('title', ''),
                            'type': link.get('type', 'unknown'),
                            'short_desc': link.get('shortDesc', ''),
                            'parent_qid': entity_data['qid'],
                            'depth': entity_data.get('depth', 0) + 1
                        })
            
            return linked_qids
            
        except Exception as e:
            logger.error(f"Error extracting linked entities: {e}")
            return []
    
    def validate_database_integrity(self, db: Session) -> Dict[str, Any]:
        """Validate that database entities match their files"""
        validation_results = {
            'total_entities': 0,
            'valid_files': 0,
            'missing_files': 0,
            'invalid_paths': 0,
            'errors': []
        }
        
        entities = db.query(Entity).all()
        validation_results['total_entities'] = len(entities)
        
        for entity in entities:
            try:
                # Check if file exists
                file_path = Path(entity.file_path)
                if not file_path.is_absolute():
                    file_path = Path("../") / file_path
                
                if file_path.exists():
                    validation_results['valid_files'] += 1
                else:
                    validation_results['missing_files'] += 1
                    validation_results['errors'].append({
                        'qid': entity.qid,
                        'error': f'File not found: {entity.file_path}'
                    })
                    
            except Exception as e:
                validation_results['invalid_paths'] += 1
                validation_results['errors'].append({
                    'qid': entity.qid,
                    'error': f'Invalid file path: {str(e)}'
                })
        
        return validation_results