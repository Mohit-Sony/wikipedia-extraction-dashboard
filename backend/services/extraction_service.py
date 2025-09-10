# backend/services/extraction_service.py
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from database.models import Entity, QueueEntry, ExtractionSession, UserDecision, ExtractionLog
from utils.schemas import (
    QueueType, EntityStatus, ExtractionStatus, ExtractionConfig, 
    ExtractionProgressUpdate, DiscoveredLinksUpdate, DeduplicationStats
)
import sys
import os

# Add Python_Helper to path for importing wiki_extract
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from Python_Helper.wiki_extract import extract_wikipedia_page_optimized

logger = logging.getLogger(__name__)

class SmartDeduplicationService:
    """Handles smart deduplication logic"""
    
    def __init__(self, db: Session):
        self.db = db
        self.stats = DeduplicationStats(
            total_checked=0,
            already_completed=0,
            already_rejected=0,
            already_in_queue=0,
            total_skipped=0,
            newly_added=0
        )
    
    def check_entity_status(self, qid: str, title: str) -> Dict[str, Any]:
        """
        Check if entity should be added to review queue or skipped
        Returns: {
            'should_add': bool,
            'reason': str,
            'existing_status': str or None
        }
        """
        self.stats.total_checked += 1
        
        # Check if entity exists in database
        entity = self.db.query(Entity).filter(Entity.qid == qid).first()
        if not entity:
            # Check by title (in case QID is different but same entity)
            entity = self.db.query(Entity).filter(Entity.title == title).first()
        
        if not entity:
            # Truly new entity
            self.stats.newly_added += 1
            return {
                'should_add': True,
                'reason': 'new_entity',
                'existing_status': None
            }
        
        # Entity exists, check its queue status
        queue_entry = self.db.query(QueueEntry).filter(QueueEntry.qid == entity.qid).first()
        
        if not queue_entry:
            # Entity exists but not in any queue (shouldn't happen, but handle it)
            self.stats.newly_added += 1
            return {
                'should_add': True,
                'reason': 'entity_exists_no_queue',
                'existing_status': entity.status
            }
        
        queue_type = queue_entry.queue_type
        
        # Decision logic based on queue status
        if queue_type == QueueType.COMPLETED.value:
            self.stats.already_completed += 1
            self.stats.total_skipped += 1
            return {
                'should_add': False,
                'reason': 'already_completed',
                'existing_status': queue_type
            }
        
        elif queue_type == QueueType.REJECTED.value:
            self.stats.already_rejected += 1
            self.stats.total_skipped += 1
            return {
                'should_add': False,
                'reason': 'already_rejected',
                'existing_status': queue_type
            }
        
        elif queue_type in [QueueType.ACTIVE.value, QueueType.ON_HOLD.value, 
                           QueueType.REVIEW.value, QueueType.PROCESSING.value, QueueType.FAILED.value]:
            self.stats.already_in_queue += 1
            self.stats.total_skipped += 1
            return {
                'should_add': False,
                'reason': f'already_in_{queue_type}_queue',
                'existing_status': queue_type
            }
        
        else:
            # Unknown status, add for review
            self.stats.newly_added += 1
            return {
                'should_add': True,
                'reason': 'unknown_status_review_needed',
                'existing_status': queue_type
            }


class ExtractionService:
    """Main extraction service that integrates with dashboard"""
    
    def __init__(self):
        self.current_session: Optional[ExtractionSession] = None
        self.is_running = False
        self.is_paused = False
        self.should_stop = False
        self.websocket_manager = None  # Will be injected
        
    def set_websocket_manager(self, manager):
        """Inject WebSocket manager for real-time updates"""
        self.websocket_manager = manager
    
    async def start_extraction(self, db: Session, queue_types: List[QueueType], 
                             config: ExtractionConfig, session_name: Optional[str] = None) -> int:
        """Start extraction process"""
        if self.is_running:
            raise ValueError("Extraction already running")
        
        # Create new extraction session
        session = ExtractionSession(
            session_name=session_name or f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            config_snapshot=config.json(),
            status="active"
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        self.current_session = session
        self.is_running = True
        self.is_paused = False
        self.should_stop = False
        
        logger.info(f"Starting extraction session {session.id}")
        
        # Notify WebSocket clients
        if self.websocket_manager:
            await self.websocket_manager.notify_extraction_status_change({
                "status": "started",
                "session_id": session.id,
                "session_name": session.session_name,
                "config": config.dict()
            })
        
        # Start extraction in background
        asyncio.create_task(self._run_extraction(db, queue_types, config))
        
        return session.id
    
    async def pause_extraction(self, db: Session) -> bool:
        """Pause current extraction"""
        if not self.is_running or self.is_paused:
            return False
        
        self.is_paused = True
        if self.current_session:
            self.current_session.status = "paused"
            db.commit()
            
            logger.info(f"Paused extraction session {self.current_session.id}")
            
            if self.websocket_manager:
                await self.websocket_manager.notify_extraction_status_change({
                    "status": "paused",
                    "session_id": self.current_session.id
                })
        
        return True
    
    async def resume_extraction(self, db: Session) -> bool:
        """Resume paused extraction"""
        if not self.is_running or not self.is_paused:
            return False
        
        self.is_paused = False
        if self.current_session:
            self.current_session.status = "active"
            db.commit()
            
            logger.info(f"Resumed extraction session {self.current_session.id}")
            
            if self.websocket_manager:
                await self.websocket_manager.notify_extraction_status_change({
                    "status": "resumed",
                    "session_id": self.current_session.id
                })
        
        return True
    
    async def cancel_extraction(self, db: Session) -> bool:
        """Cancel current extraction"""
        if not self.is_running:
            return False
        
        self.should_stop = True
        self.is_running = False
        self.is_paused = False
        
        if self.current_session:
            self.current_session.status = "cancelled"
            self.current_session.end_time = datetime.utcnow()
            db.commit()
            
            logger.info(f"Cancelled extraction session {self.current_session.id}")
            
            if self.websocket_manager:
                await self.websocket_manager.notify_extraction_status_change({
                    "status": "cancelled",
                    "session_id": self.current_session.id
                })
        
        return True
    
    def get_extraction_status(self, db: Session) -> Dict[str, Any]:
        """Get current extraction status"""
        if not self.current_session:
            return {
                "status": "idle",
                "session_id": None,
                "progress_percentage": 0,
                "current_entity": None
            }
        
        # Calculate progress
        total_entities = db.query(QueueEntry).filter(
            QueueEntry.queue_type == QueueType.PROCESSING.value
        ).count()
        
        processed_entities = self.current_session.total_extracted + self.current_session.total_errors
        
        progress = 0
        if total_entities > 0:
            progress = (processed_entities / total_entities) * 100
        
        return {
            "status": "running" if self.is_running and not self.is_paused else 
                     "paused" if self.is_paused else "idle",
            "session_id": self.current_session.id,
            "session_name": self.current_session.session_name,
            "progress_percentage": progress,
            "current_entity": self.current_session.current_entity_qid,
            "total_entities": total_entities,
            "processed_entities": processed_entities,
            "failed_entities": self.current_session.total_errors,
            "skipped_entities": self.current_session.total_skipped,
            "start_time": self.current_session.start_time,
            "estimated_completion": self._estimate_completion_time(total_entities, processed_entities)
        }
    
    async def _run_extraction(self, db: Session, queue_types: List[QueueType], config: ExtractionConfig):
        """Main extraction loop"""
        try:
            # Get entities to process
            entities_to_process = self._get_entities_for_extraction(db, queue_types)
            
            if not entities_to_process:
                logger.info("No entities to process")
                await self._complete_extraction(db, "completed")
                return
            
            # Move entities to PROCESSING queue
            for entity in entities_to_process:
                self._move_entity_to_processing(db, entity)
            
            # Store entity info safely to avoid session binding issues
            entity_info_list = [(entity.qid, entity.title) for entity in entities_to_process]
            total_entities = len(entity_info_list)
            processed_count = 0
            
            logger.info(f"Starting extraction of {total_entities} entities")
            
            for entity_qid, entity_title in entity_info_list:
                if self.should_stop:
                    break
                
                # Wait if paused
                while self.is_paused and not self.should_stop:
                    await asyncio.sleep(1)
                
                if self.should_stop:
                    break
                
                # Get fresh entity from database for each iteration to avoid session issues
                entity = db.query(Entity).filter(Entity.qid == entity_qid).first()
                if not entity:
                    logger.error(f"Entity {entity_qid} not found, skipping")
                    processed_count += 1
                    continue
                
                # Update current entity
                self.current_session.current_entity_qid = entity_qid
                self.current_session.progress_percentage = (processed_count / total_entities) * 100
                db.commit()
                
                # Notify progress
                if self.websocket_manager:
                    await self.websocket_manager.notify_extraction_progress({
                        "session_id": self.current_session.id,
                        "current_entity_qid": entity_qid,
                        "current_entity_title": entity_title,
                        "progress_percentage": self.current_session.progress_percentage,
                        "processed_count": processed_count,
                        "total_count": total_entities
                    })
                
                # Extract entity
                success = await self._extract_single_entity(db, entity, config)
                
                processed_count += 1
                
                if success:
                    self.current_session.total_extracted += 1
                else:
                    self.current_session.total_errors += 1
                
                # Commit session stats
                try:
                    db.commit()
                except Exception as commit_error:
                    logger.error(f"Error committing session stats: {commit_error}")
                    try:
                        db.rollback()
                    except:
                        pass
                
                # Pause between requests
                await asyncio.sleep(config.pause_between_requests)
            
            # Complete extraction
            status = "cancelled" if self.should_stop else "completed"
            await self._complete_extraction(db, status)
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            await self._complete_extraction(db, "failed")

    async def _extract_single_entity(self, db: Session, entity: Entity, config: ExtractionConfig) -> bool:
        """Extract a single entity and process its links"""
        entity_qid = entity.qid  # Store QID for safe reference
        entity_title = entity.title  # Store title for safe reference
        
        try:
            # Log extraction start
            self._log_extraction_event(db, "started", entity_qid, {"title": entity_title})
            
            # Perform extraction
            extracted_data = await extract_wikipedia_page_optimized(entity_title)

            if not extracted_data:
                self._log_extraction_event(db, "failed", entity_qid, {"error": "No data returned"})
                entity.status = EntityStatus.FAILED.value
                self._move_entity_to_queue(db, entity, QueueType.FAILED)
                return False
            
            # Save extracted data (implement this based on your file service)
            from services.file_service import FileService
            file_service = FileService()
            
            # Determine entity type from extracted data or default to 'unknown'
            entity_type = str(extracted_data.get('type', 'unknown')).replace(' ', '_').replace('/', '_')
            
            # Save to file system
            file_saved = file_service.save_entity_data(entity_qid, entity_type, extracted_data)
            
            if not file_saved:
                logger.warning(f"Failed to save file for entity {entity_qid}, but continuing with database update")
                # Don't fail the entire extraction, just log the issue
            

            # Update entity with extracted metadata
            entity.entity_type = entity_type  # Update entity type from extracted data
            entity.num_links = len(extracted_data.get('links', {}).get('internal_links', []))
            entity.num_tables = len(extracted_data.get('tables', []))
            entity.num_images = len(extracted_data.get('images', []))
            entity.num_chunks = len(extracted_data.get('chunks', []))
            entity.page_length = extracted_data.get('metadata', {}).get('page_length', 0)
            entity.extraction_date = datetime.utcnow()
            entity.status = EntityStatus.COMPLETED.value
            
            # Move to completed queue
            self._move_entity_to_queue(db, entity, QueueType.COMPLETED)
            
            # Process discovered links with smart deduplication
            if config.auto_add_to_review:
                await self._process_discovered_links(db, entity, extracted_data)
            
            # After processing links, refresh entity from database in case of rollbacks
            try:
                db.refresh(entity)
            except Exception as refresh_error:
                # If refresh fails, re-query the entity
                logger.warning(f"Could not refresh entity {entity_qid}, re-querying: {refresh_error}")
                entity = db.query(Entity).filter(Entity.qid == entity_qid).first()
                if not entity:
                    logger.error(f"Entity {entity_qid} not found after re-query")
                    return False
            
            # Log completion with safely accessed attributes
            self._log_extraction_event(db, "completed", entity_qid, {
                "num_links": entity.num_links,
                "num_tables": entity.num_tables,
                "num_images": entity.num_images,
                "page_length": entity.page_length
            })
            
            return True
            
        except Exception as e:
            try:
                db.rollback()  # Rollback the failed transaction
                logger.error(f"Failed to extract entity {entity_qid}: {e}")
                self._log_extraction_event(db, "failed", entity_qid, {"error": str(e)})
                
                # Re-query entity after rollback to ensure it's bound to session
                entity = db.query(Entity).filter(Entity.qid == entity_qid).first()
                if entity:
                    entity.status = EntityStatus.FAILED.value
                    self._move_entity_to_queue(db, entity, QueueType.FAILED)
                    db.commit()  # Commit the status change
                else:
                    logger.error(f"Could not find entity {entity_qid} to update status")
                    
            except Exception as rollback_error:
                logger.error(f"Error during rollback for entity {entity_qid}: {rollback_error}")
                try:
                    db.rollback()  # Final attempt to clean state
                except:
                    pass
            return False
        
    async def _process_discovered_links(self, db: Session, parent_entity: Entity, extracted_data: Dict):
        """Process discovered links with smart deduplication"""
        internal_links = extracted_data.get('links', {}).get('internal_links', [])
        
        if not internal_links:
            return
        
        dedup_service = SmartDeduplicationService(db)
        added_to_review = 0
        skip_reasons = {}
        processing_errors = 0
        
        for link in internal_links:
            qid = link.get('qid')
            title = link.get('title')
            
            if not qid or not title:
                continue
            
            try:
                # Check deduplication
                check_result = dedup_service.check_entity_status(qid, title)
                
                if check_result['should_add']:
                    # Ensure type and description are never None
                    entity_type = link.get('type') or 'unknown'
                    entity_short_desc = link.get('shortDesc') or f"Entity discovered from {parent_entity.title}"
                    
                    # Create new entity and add to review queue
                    new_entity = Entity(
                        qid=qid,
                        title=title,
                        type=entity_type,
                        short_desc=entity_short_desc,
                        status=EntityStatus.UNPROCESSED.value,
                        parent_qid=parent_entity.qid,
                        depth=parent_entity.depth + 1,
                        discovered_by=parent_entity.qid,
                        file_path=f"placeholder/{qid}.json"
                    )
                    
                    db.add(new_entity)
                    db.flush()  # Get ID
                    
                    # Add to review queue
                    queue_entry = QueueEntry(
                        qid=qid,
                        queue_type=QueueType.REVIEW.value,
                        priority=2,  # Medium priority
                        added_by="extraction_service",
                        discovery_source=parent_entity.qid,
                        notes=f"Discovered from {parent_entity.title}"
                    )
                    
                    db.add(queue_entry)
                    added_to_review += 1
                    
                    # Log decision
                    decision = UserDecision(
                        qid=qid,
                        session_id=self.current_session.id,
                        decision_type="discovered_link",
                        decision_value="added_to_review",
                        auto_decision=True,
                        reasoning=f"New entity discovered from {parent_entity.title}"
                    )
                    db.add(decision)
                    
                else:
                    # Log skipped entity
                    reason = check_result['reason']
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    
                    decision = UserDecision(
                        qid=qid,
                        session_id=self.current_session.id,
                        decision_type="skip_duplicate",
                        decision_value=reason,
                        auto_decision=True,
                        reasoning=f"Skipped: {reason}, existing status: {check_result['existing_status']}"
                    )
                    db.add(decision)
                    
            except Exception as e:
                processing_errors += 1
                logger.error(f"Error processing link {qid} ({title}): {e}")
                
                # Handle database rollback
                try:
                    db.rollback()
                    logger.info(f"Session rolled back for failed link: {qid}")
                except Exception as rollback_error:
                    logger.error(f"Error during rollback while processing link {qid}: {rollback_error}")
                    # Force clean state
                    try:
                        db.close()
                        # Note: You might need to recreate the session here depending on your setup
                    except:
                        pass
                
                # Continue processing remaining links
                continue
        
        # Commit all successful operations
        try:
            # Update session stats
            self.current_session.total_skipped += dedup_service.stats.total_skipped
            db.commit()
            
            logger.info(f"Successfully processed {len(internal_links)} links from {parent_entity.title}: "
                    f"{added_to_review} added to review, {dedup_service.stats.total_skipped} skipped, "
                    f"{processing_errors} errors")
            
        except Exception as commit_error:
            logger.error(f"Error committing processed links for {parent_entity.title}: {commit_error}")
            try:
                db.rollback()
            except:
                pass
            return  # Exit early if we can't commit
        
        # Log discovered links event
        try:
            self._log_extraction_event(db, "discovered_links", parent_entity.qid, {
                "total_links": len(internal_links),
                "added_to_review": added_to_review,
                "skipped_duplicates": dedup_service.stats.total_skipped,
                "processing_errors": processing_errors,
                "skip_reasons": skip_reasons,
                "deduplication_stats": dedup_service.stats.dict()
            })
        except Exception as log_error:
            logger.error(f"Error logging extraction event: {log_error}")
            # Continue even if logging fails
        
        # Notify WebSocket clients
        try:
            if self.websocket_manager:
                await self.websocket_manager.notify_links_discovered({
                    "session_id": self.current_session.id,
                    "parent_qid": parent_entity.qid,
                    "parent_title": parent_entity.title,
                    "discovered_count": len(internal_links),
                    "added_to_review": added_to_review,
                    "skipped_duplicates": dedup_service.stats.total_skipped,
                    "processing_errors": processing_errors,
                    "skipped_reasons": skip_reasons
                })
        except Exception as websocket_error:
            logger.error(f"Error notifying WebSocket clients: {websocket_error}")
            # Continue even if WebSocket notification fails  
        
    def _get_entities_for_extraction(self, db: Session, queue_types: List[QueueType]) -> List[Entity]:
        """Get entities ready for extraction"""
        queue_type_values = [qt.value for qt in queue_types]
        
        entities = db.query(Entity).join(QueueEntry).filter(
            QueueEntry.queue_type.in_(queue_type_values)
        ).order_by(QueueEntry.priority, QueueEntry.added_date).all()
        
        return entities
    
    def _move_entity_to_processing(self, db: Session, entity: Entity):
        """Move entity to processing queue"""
        self._move_entity_to_queue(db, entity, QueueType.PROCESSING)
        entity.status = EntityStatus.PROCESSING.value
    
    def _move_entity_to_queue(self, db: Session, entity: Entity, queue_type: QueueType):
        """Move entity to specified queue"""
        # Update existing queue entry
        queue_entry = db.query(QueueEntry).filter(QueueEntry.qid == entity.qid).first()
        if queue_entry:
            queue_entry.queue_type = queue_type.value
            queue_entry.processed_date = datetime.utcnow() if queue_type in [QueueType.COMPLETED, QueueType.FAILED] else None
        else:
            # Create new queue entry
            queue_entry = QueueEntry(
                qid=entity.qid,
                queue_type=queue_type.value,
                added_by="extraction_service"
            )
            db.add(queue_entry)
    
    def _log_extraction_event(self, db: Session, event_type: str, qid: str, event_data: Dict):
        """Log extraction event"""
        if self.current_session:
            log_entry = ExtractionLog(
                session_id=self.current_session.id,
                qid=qid,
                event_type=event_type,
                event_data=event_data,
                message=f"Entity {qid}: {event_type}"
            )
            db.add(log_entry)
    
    async def _complete_extraction(self, db: Session, status: str):
        """Complete extraction session"""
        if self.current_session:
            self.current_session.status = status
            self.current_session.end_time = datetime.utcnow()
            self.current_session.progress_percentage = 100.0
            db.commit()
            
            logger.info(f"Extraction session {self.current_session.id} completed with status: {status}")
            
            if self.websocket_manager:
                await self.websocket_manager.notify_extraction_status_change({
                    "status": status,
                    "session_id": self.current_session.id,
                    "total_extracted": self.current_session.total_extracted,
                    "total_errors": self.current_session.total_errors,
                    "total_skipped": self.current_session.total_skipped
                })
        
        self.is_running = False
        self.is_paused = False
        self.should_stop = False
        self.current_session = None
    
    def _estimate_completion_time(self, total_entities: int, processed_entities: int) -> Optional[datetime]:
        """Estimate completion time based on current progress"""
        if not self.current_session or processed_entities == 0:
            return None
        
        elapsed_time = datetime.utcnow() - self.current_session.start_time
        avg_time_per_entity = elapsed_time.total_seconds() / processed_entities
        remaining_entities = total_entities - processed_entities
        
        if remaining_entities <= 0:
            return datetime.utcnow()
        
        estimated_remaining_seconds = remaining_entities * avg_time_per_entity
        return datetime.utcnow() + timedelta(seconds=estimated_remaining_seconds)


# Global extraction service instance
extraction_service = ExtractionService()