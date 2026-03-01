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

    def _is_extraction_valid(self, extracted_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate if extracted data is meaningful and complete
        Returns: (is_valid, reason)
        """
        if not extracted_data:
            return False, "No data returned from extraction"

        # Extract counts
        num_links = len(extracted_data.get('links', {}).get('internal_links', []))
        num_tables = len(extracted_data.get('tables', []))
        num_images = len(extracted_data.get('images', []))
        num_chunks = len(extracted_data.get('chunks', []))
        page_length = extracted_data.get('metadata', {}).get('page_length', 0)

        # Check if all critical fields are zero/empty
        if num_links == 0 and num_tables == 0 and num_images == 0 and num_chunks == 0 and page_length == 0:
            return False, "Extraction returned empty data (all counts are 0)"

        # Check if at least we have chunks or page_length (minimum requirement)
        if num_chunks == 0 and page_length == 0:
            return False, "No content chunks or page length - extraction incomplete"

        # Additional validation: check if content structure exists
        if 'content' not in extracted_data and 'chunks' not in extracted_data:
            return False, "Missing content structure in extracted data"

        return True, "Valid extraction"
        
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


    def print_entity_debug_info(self ,entity, label="Entity"):
        """Helper function to print meaningful entity information"""
        if entity:
            print(f"\n=== {label} ===")
            print(f"QID: {entity.qid}")
            print(f"Title: {entity.title}")
            print(f"Type: {entity.type}")
            print(f"Status: {entity.status}")
            print(f"Links: {entity.num_links}")
            print(f"Tables: {entity.num_tables}")
            print(f"Images: {entity.num_images}")
            print(f"Chunks: {entity.num_chunks}")
            print(f"Page Length: {entity.page_length}")
            print(f"Extraction Date: {entity.extraction_date}")
            print(f"File Path: {entity.file_path}")
            print(f"Created At: {entity.created_at}")
            print(f"Updated At: {entity.updated_at}")
        else:
            print(f"\n=== {label} ===")
            print("Entity is None!")

    def print_dirty_objects_details(self, db, label="Dirty Objects"):
        """Print detailed information about dirty objects in session - FIXED VERSION"""
        print(f"\n=== {label} ===")
        if db.dirty:
            print(f"Count: {len(db.dirty)}")
            for i, obj in enumerate(db.dirty):
                print(f"\n  Dirty Object #{i+1}:")
                print(f"    Type: {type(obj).__name__}")
                
                if hasattr(obj, 'qid'):
                    print(f"    QID: {obj.qid}")
                if hasattr(obj, 'title'):
                    print(f"    Title: {obj.title}")
                if hasattr(obj, 'queue_type'):
                    print(f"    Queue Type: {obj.queue_type}")
                if hasattr(obj, 'status'):
                    print(f"    Status: {obj.status}")
                if hasattr(obj, 'num_links'):
                    print(f"    Links: {obj.num_links}")
                    
                # FIXED: Show what changed (SQLAlchemy history tracking)
                from sqlalchemy import inspect
                state = inspect(obj)
                
                try:
                    # Check if modified is a boolean or collection
                    if hasattr(state, 'modified'):
                        modified_attrs = state.modified
                        
                        # Handle different return types
                        if isinstance(modified_attrs, bool):
                            if modified_attrs:
                                print(f"    Has Changes: Yes (boolean response)")
                                # Try to get actual changed attributes through history
                                print(f"    Checking individual attributes...")
                                for attr_name in ['qid', 'title', 'status', 'num_links', 'num_tables', 'num_images', 'num_chunks', 'page_length', 'extraction_date', 'type']:
                                    if hasattr(obj, attr_name) and hasattr(state.attrs, attr_name):
                                        try:
                                            history = state.attrs[attr_name].history
                                            if history.has_changes():
                                                print(f"      {attr_name}: CHANGED")
                                        except:
                                            pass
                            else:
                                print(f"    Has Changes: No")
                        
                        elif modified_attrs:  # It's a collection/set
                            print(f"    Modified Attributes: {list(modified_attrs)}")
                            for attr in modified_attrs:
                                try:
                                    history = state.attrs[attr].history
                                    if history.has_changes():
                                        old_val = history.deleted[0] if history.deleted else None
                                        new_val = history.added[0] if history.added else None
                                        print(f"      {attr}: {old_val} -> {new_val}")
                                except Exception as hist_error:
                                    print(f"      {attr}: (history error: {hist_error})")
                        else:
                            print(f"    Modified Attributes: None")
                            
                    else:
                        print(f"    Modified Attributes: Not available")
                        
                except Exception as debug_error:
                    print(f"    Debug Error: {debug_error}")
                    print(f"    State type: {type(state)}")
                    print(f"    State dir: {[attr for attr in dir(state) if not attr.startswith('_')]}")
                    
        else:
            print("No dirty objects")

    # ALTERNATIVE SIMPLER VERSION (if the above is too complex):
    def print_dirty_objects_simple(self, db, label="Dirty Objects"):
        """Simplified version that avoids the iteration error"""
        print(f"\n=== {label} ===")
        if db.dirty:
            print(f"Count: {len(db.dirty)}")
            for i, obj in enumerate(db.dirty):
                print(f"\n  Dirty Object #{i+1}:")
                print(f"    Type: {type(obj).__name__}")
                
                if hasattr(obj, 'qid'):
                    print(f"    QID: {obj.qid}")
                if hasattr(obj, 'title'):
                    print(f"    Title: {obj.title}")
                if hasattr(obj, 'status'):
                    print(f"    Status: {obj.status}")
                if hasattr(obj, 'num_links'):
                    print(f"    Links: {obj.num_links}")
                
                # SAFE: Just show that it's modified without details
                from sqlalchemy import inspect
                state = inspect(obj)
                print(f"    Is Modified: {bool(state.modified) if hasattr(state, 'modified') else 'Unknown'}")
                
        else:
            print("No dirty objects")

    async def _extract_single_entity(self, db: Session, entity: Entity, config: ExtractionConfig) -> bool:
        """Extract a single entity and process its links - DEEPLY FIXED VERSION"""
        entity_qid = entity.qid  # Store QID for safe reference
        entity_title = entity.title  # Store title for safe reference
        
        # === BEFORE CHANGES DEBUG ===
        print(f"\n{'='*60}")
        print(f"STARTING EXTRACTION FOR: {entity_qid} - {entity_title}")
        print(f"{'='*60}")
        
        # self.print_entity_debug_info(entity, "ORIGINAL ENTITY (Potentially Detached)")
        #self.print_dirty_objects_details(db, "DIRTY OBJECTS BEFORE RE-QUERY")
        
        try:
            # === CRITICAL FIX 1: Fresh Entity Query ===
            print(f"\n{'='*50}")
            print(f"GETTING FRESH ENTITY FROM DATABASE")
            print(f"{'='*50}")
            
            fresh_entity = db.query(Entity).filter(Entity.qid == entity_qid).first()
            if not fresh_entity:
                logger.error(f"Entity {entity_qid} not found in database")
                return False
            
            # Replace the potentially detached entity with fresh one
            entity = fresh_entity
            
            # === CRITICAL FIX 2: Verify Session Attachment ===
            from sqlalchemy import inspect
            entity_state = inspect(entity)
            print(f"\n=== ENTITY SESSION STATE CHECK ===")
            print(f"Entity in session: {entity in db}")
            print(f"Entity session: {entity_state.session}")
            print(f"Current session: {db}")
            print(f"Entity detached: {entity_state.detached}")
            print(f"Entity persistent: {entity_state.persistent}")
            
            if entity_state.detached:
                print("⚠️ Entity is detached! Re-attaching...")
                db.add(entity)
                db.flush()  # Force attachment without commit
            
            # self.print_entity_debug_info(entity, "FRESH ENTITY AFTER SESSION CHECK")
            #self.print_dirty_objects_details(db, "DIRTY OBJECTS AFTER FRESH QUERY")

            # Log extraction start
            self._log_extraction_event(db, "started", entity_qid, {"title": entity_title})
            
            # Perform extraction
            extracted_data = await extract_wikipedia_page_optimized(entity_title)

            # Validate extracted data
            is_valid, validation_reason = self._is_extraction_valid(extracted_data)

            if not is_valid:
                self._log_extraction_event(db, "failed", entity_qid, {
                    "error": validation_reason,
                    "extracted_data_available": extracted_data is not None
                })
                entity.status = EntityStatus.FAILED.value
                self._move_entity_to_queue(db, entity, QueueType.FAILED)
                db.commit()
                logger.warning(f"Entity {entity_qid} extraction failed validation: {validation_reason}")
                return False
            
            # Save extracted data to file system
            from services.file_service import FileService
            file_service = FileService()
            
            # Get entity type from extracted data, but preserve existing type if extraction failed
            extracted_type = extracted_data.get('type')
            if extracted_type and extracted_type != 'None' and str(extracted_type).lower() != 'none':
                entity_type = str(extracted_type).replace(' ', '_').replace('/', '_')
            else:
                # If extraction didn't return a type, keep the existing entity type
                entity_type = entity.type if entity.type else 'unknown'
                logger.warning(f"Extraction didn't return type for {entity_qid}, using existing type: {entity_type}")

            file_saved = file_service.save_entity_data(entity_qid, entity_type, extracted_data)

            if not file_saved:
                logger.warning(f"Failed to save file for entity {entity_qid}, but continuing with database update")

            # === CRITICAL FIX 3: Verify Entity is Tracked Before Changes ===
            print(f"\n{'='*50}")
            print(f"MAKING CHANGES TO ENTITY")
            print(f"{'='*50}")

            # Test tracking BEFORE making changes
            test_change = entity.updated_at  # Read current value
            entity.updated_at = datetime.now()  # Make test change

            print(f"After test change - Entity in dirty set: {entity in db.dirty}")
            if entity not in db.dirty:
                print("🚨 CRITICAL: Entity changes not being tracked!")
                print("Attempting to force tracking...")
                db.add(entity)  # Force re-attachment
                entity.updated_at = datetime.now()  # Make change again
                print(f"After force re-attach - Entity in dirty set: {entity in db.dirty}")
            else:
                print("✅ Entity changes are being tracked")

            # Store old values for comparison
            old_values = {
                'num_links': entity.num_links,
                'num_tables': entity.num_tables,
                'num_images': entity.num_images,
                'num_chunks': entity.num_chunks,
                'page_length': entity.page_length,
                'status': entity.status
            }

            # === MAKE ACTUAL CHANGES ===
            # Only update type if we have a valid extracted type
            if extracted_type and extracted_type != 'None' and str(extracted_type).lower() != 'none':
                entity.type = entity_type
            entity.num_links = len(extracted_data.get('links', {}).get('internal_links', []))
            entity.num_tables = len(extracted_data.get('tables', []))
            entity.num_images = len(extracted_data.get('images', []))
            entity.num_chunks = len(extracted_data.get('chunks', []))
            entity.page_length = extracted_data.get('metadata', {}).get('page_length', 0)
            entity.extraction_date = datetime.now()
            entity.status = EntityStatus.COMPLETED.value
            
            # Print what changed
            new_values = {
                'num_links': entity.num_links,
                'num_tables': entity.num_tables,
                'num_images': entity.num_images,
                'num_chunks': entity.num_chunks,
                'page_length': entity.page_length,
                'status': entity.status
            }
            
            print("\n=== CHANGES MADE ===")
            for key in old_values:
                if old_values[key] != new_values[key]:
                    print(f"  {key}: {old_values[key]} -> {new_values[key]}")

            print(f'Entity changes after metadata update: {entity.num_tables}, {entity.status}')

            # === CRITICAL FIX 4: Verify Changes Are Tracked ===
            # self.print_entity_debug_info(entity, "ENTITY AFTER CHANGES")
            #self.print_dirty_objects_details(db, "DIRTY OBJECTS AFTER CHANGES")
            
            print(f"Entity in dirty set after changes: {entity in db.dirty}")
            if entity not in db.dirty:
                print("🚨 PANIC: Entity changes STILL not tracked!")
                return False

            # === CRITICAL FIX 5: Separate Queue Operations ===
            print(f"\n{'='*50}")
            print(f"UPDATING QUEUE STATUS")
            print(f"{'='*50}")
            
            # Move to completed queue (this creates/modifies QueueEntry)
            self._move_entity_to_queue(db, entity, QueueType.COMPLETED)
            
            print(f"Dirty objects after queue move: {len(db.dirty)}")
            #self.print_dirty_objects_details(db, "DIRTY OBJECTS AFTER QUEUE MOVE")

            # === COMMIT CHANGES ===
            print(f"\n{'='*50}")
            print(f"COMMITTING CHANGES TO DATABASE")
            print(f"{'='*50}")
            
            try:
                print(f"Dirty objects before commit: {db.dirty}")
                
                # Force flush before commit to see what happens
                db.flush()
                print("✅ Flush successful")
                
                db.commit()
                logger.info(f"Committed extraction metadata for entity {entity_qid}")
                print("✅ COMMIT SUCCESSFUL")
                
            except Exception as commit_error:
                logger.error(f"Failed to commit extraction metadata for {entity_qid}: {commit_error}")
                print(f"❌ COMMIT FAILED: {commit_error}")
                db.rollback()
                return False

            print(f"Dirty objects after commit: {db.dirty}")

            # === VERIFICATION ===
            # self.print_entity_debug_info(entity, "ENTITY AFTER COMMIT (Local Object)")
            #self.print_dirty_objects_details(db, "DIRTY OBJECTS AFTER COMMIT")
            
            # === FRESH ENTITY FROM DATABASE ===
            print(f"\n{'='*50}")
            print(f"FETCHING FRESH ENTITY FROM DATABASE FOR VERIFICATION")
            print(f"{'='*50}")
            
            verification_entity = db.query(Entity).filter(Entity.qid == entity_qid).first()
            # self.print_entity_debug_info(verification_entity, "VERIFICATION ENTITY FROM DATABASE")
            
            # Compare local vs fresh
            print(f"\n=== LOCAL VS FRESH COMPARISON ===")
            if verification_entity:
                fields_to_compare = ['num_links', 'num_tables', 'num_images', 'num_chunks', 'page_length', 'status']
                all_match = True
                for field in fields_to_compare:
                    local_val = getattr(entity, field)
                    fresh_val = getattr(verification_entity, field)
                    match_status = "✅ MATCH" if local_val == fresh_val else "❌ MISMATCH"
                    if local_val != fresh_val:
                        all_match = False
                    print(f"  {field}: Local={local_val}, Fresh={fresh_val} {match_status}")
                
                if not all_match:
                    print("🚨 DATA PERSISTENCE FAILURE DETECTED!")
                    return False
                else:
                    print("✅ ALL DATA SUCCESSFULLY PERSISTED!")
            
            # Process discovered links (separate transaction)
            if config.auto_add_to_review:
                await self._process_discovered_links(db, entity, extracted_data)
            
            # Final session state check
            try:
                _ = entity.id
                print("✅ Entity still bound to session after link processing")
            except Exception as detached_error:
                print(f"⚠️ Entity detached during link processing: {detached_error}")
                entity = db.query(Entity).filter(Entity.qid == entity_qid).first()
                if not entity:
                    logger.error(f"Entity {entity_qid} not found after re-query")
                    return False
            
            # Log completion
            self._log_extraction_event(db, "completed", entity_qid, {
                "num_links": entity.num_links,
                "num_tables": entity.num_tables,
                "num_images": entity.num_images,
                "page_length": entity.page_length,
                "file_saved": file_saved
            })
            
            print(f"\n{'='*60}")
            print(f"EXTRACTION COMPLETED SUCCESSFULLY FOR: {entity_qid}")
            print(f"{'='*60}\n")
            
            return True
            
        except Exception as e:
            print(f"\n❌ EXTRACTION FAILED FOR {entity_qid}: {e}")
            try:
                db.rollback()
                logger.error(f"Failed to extract entity {entity_qid}: {e}")
                self._log_extraction_event(db, "failed", entity_qid, {"error": str(e)})
                
                # Get fresh entity for failure handling
                entity = db.query(Entity).filter(Entity.qid == entity_qid).first()
                if entity:
                    entity.status = EntityStatus.FAILED.value
                    self._move_entity_to_queue(db, entity, QueueType.FAILED)
                    db.commit()
                    
            except Exception as rollback_error:
                logger.error(f"Error during rollback for entity {entity_qid}: {rollback_error}")
                
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
            title = link.get("redirectTitle") or link.get("title")
            
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
                        file_path=f"wikipedia_data/{entity_type}/{qid}.json"
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