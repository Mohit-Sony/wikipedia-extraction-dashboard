# backend/api/extraction.py
# backend/api/extraction.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import Entity, QueueEntry, ExtractionSession
from utils.schemas import (
    ExtractionStartRequest, ExtractionStatusResponse, ExtractionConfig,
    QueueType, ManualEntityCreate, ManualEntityResponse,
    ExtractionStatus
)
from services.extraction_service import extraction_service
from services.file_service import FileService
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/extraction/start")
async def start_extraction(
    request: ExtractionStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start extraction process for entities in specified queues"""
    try:
        # Validate queue types
        if not request.queue_types:
            raise HTTPException(status_code=400, detail="At least one queue type must be specified")
        
        # Check if any entities exist in specified queues
        entity_count = db.query(QueueEntry).filter(
            QueueEntry.queue_type.in_([qt.value for qt in request.queue_types])
        ).count()
        
        if entity_count == 0:
            raise HTTPException(status_code=400, detail="No entities found in specified queues")
        
        # Use default config if not provided
        config = request.config or ExtractionConfig()
        
        # Start extraction
        # print(    >>>>>>>>        db,
        #     request.queue_types,
        #     " >>>>>>>>>> config ",config,
        #     " >>>>>>>>>> session_name" , request.session_name)
        session_id = await extraction_service.start_extraction(
            db=db,
            queue_types=request.queue_types,
            config=config,
            session_name=request.session_name
        )
        
        return {
            "message": "Extraction started successfully",
            "session_id": session_id,
            "entities_to_process": entity_count,
            "config": config.dict()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start extraction: {e}")
        raise HTTPException(status_code=500, detail="Failed to start extraction")

@router.post("/extraction/pause")
async def pause_extraction(db: Session = Depends(get_db)):
    """Pause current extraction"""
    try:
        success = await extraction_service.pause_extraction(db)
        if not success:
            raise HTTPException(status_code=400, detail="No active extraction to pause")
        
        return {"message": "Extraction paused successfully"}
        
    except Exception as e:
        logger.error(f"Failed to pause extraction: {e}")
        raise HTTPException(status_code=500, detail="Failed to pause extraction")

@router.post("/extraction/resume")
async def resume_extraction(db: Session = Depends(get_db)):
    """Resume paused extraction"""
    try:
        success = await extraction_service.resume_extraction(db)
        if not success:
            raise HTTPException(status_code=400, detail="No paused extraction to resume")
        
        return {"message": "Extraction resumed successfully"}
        
    except Exception as e:
        logger.error(f"Failed to resume extraction: {e}")
        raise HTTPException(status_code=500, detail="Failed to resume extraction")

@router.post("/extraction/cancel")
async def cancel_extraction(db: Session = Depends(get_db)):
    """Cancel current extraction"""
    try:
        success = await extraction_service.cancel_extraction(db)
        if not success:
            raise HTTPException(status_code=400, detail="No active extraction to cancel")
        
        return {"message": "Extraction cancelled successfully"}
        
    except Exception as e:
        logger.error(f"Failed to cancel extraction: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel extraction")

@router.get("/extraction/status", response_model=ExtractionStatusResponse)
async def get_extraction_status(db: Session = Depends(get_db)):
    """Get current extraction status"""
    try:
        status = extraction_service.get_extraction_status(db)
        return ExtractionStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Failed to get extraction status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get extraction status")

@router.post("/extraction/configure")
async def update_extraction_config(
    config: ExtractionConfig,
    db: Session = Depends(get_db)
):
    """Update extraction configuration"""
    try:
        # Save config as user preference
        from database.models import UserPreference
        import json
        
        # Remove existing config preference
        db.query(UserPreference).filter(
            UserPreference.preference_type == "extraction_config",
            UserPreference.preference_name == "default"
        ).delete()
        
        # Add new config
        pref = UserPreference(
            preference_type="extraction_config",
            preference_name="default",
            preference_value=json.dumps(config.dict())
        )
        db.add(pref)
        db.commit()
        
        return {
            "message": "Extraction configuration updated successfully",
            "config": config.dict()
        }
        
    except Exception as e:
        logger.error(f"Failed to update extraction config: {e}")
        raise HTTPException(status_code=500, detail="Failed to update extraction config")

@router.get("/extraction/config", response_model=ExtractionConfig)
async def get_extraction_config(db: Session = Depends(get_db)):
    """Get current extraction configuration"""
    try:
        from database.models import UserPreference
        import json
        
        pref = db.query(UserPreference).filter(
            UserPreference.preference_type == "extraction_config",
            UserPreference.preference_name == "default"
        ).first()
        
        if pref:
            config_data = json.loads(pref.preference_value)
            return ExtractionConfig(**config_data)
        else:
            # Return default config
            return ExtractionConfig()
            
    except Exception as e:
        logger.error(f"Failed to get extraction config: {e}")
        return ExtractionConfig()  # Return default on error

@router.get("/extraction/sessions")
async def get_extraction_sessions(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get extraction session history"""
    try:
        sessions = db.query(ExtractionSession).order_by(
            ExtractionSession.start_time.desc()
        ).offset(offset).limit(limit).all()
        
        total = db.query(ExtractionSession).count()
        
        return {
            "sessions": [
                {
                    "id": session.id,
                    "session_name": session.session_name,
                    "start_time": session.start_time,
                    "end_time": session.end_time,
                    "status": session.status,
                    "total_extracted": session.total_extracted,
                    "total_errors": session.total_errors,
                    "total_skipped": session.total_skipped,
                    "progress_percentage": session.progress_percentage
                }
                for session in sessions
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get extraction sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get extraction sessions")

@router.get("/extraction/sessions/{session_id}/logs")
async def get_session_logs(
    session_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get logs for specific extraction session"""
    try:
        from database.models import ExtractionLog
        
        logs = db.query(ExtractionLog).filter(
            ExtractionLog.session_id == session_id
        ).order_by(
            ExtractionLog.timestamp.desc()
        ).offset(offset).limit(limit).all()
        
        total = db.query(ExtractionLog).filter(
            ExtractionLog.session_id == session_id
        ).count()
        
        return {
            "logs": [
                {
                    "id": log.id,
                    "qid": log.qid,
                    "event_type": log.event_type,
                    "event_data": log.event_data,
                    "message": log.message,
                    "timestamp": log.timestamp
                }
                for log in logs
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get session logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get session logs")

@router.post("/entities/manual", response_model=ManualEntityResponse)
async def add_manual_entity(
    entity_data: ManualEntityCreate,
    db: Session = Depends(get_db)
):
    """Manually add entity to the system"""
    try:
        # Generate QID (you might want to use a different strategy)
        qid = f"Q{abs(hash(entity_data.title)) % 10000000}"
        
        # Check if entity already exists
        existing = db.query(Entity).filter(
            (Entity.qid == qid) | (Entity.title == entity_data.title)
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Entity already exists")
        
        # Create entity
        entity = Entity(
            qid=qid,
            title=entity_data.title,
            type=entity_data.type,
            short_desc=entity_data.short_desc,
            status="unprocessed",
            file_path=f"manual/{qid}.json",
            depth=0
        )
        
        db.add(entity)
        db.flush()
        
        # Add to specified queue
        queue_entry = QueueEntry(
            qid=qid,
            queue_type=entity_data.add_to_queue.value,
            priority=entity_data.priority.value,
            added_by="manual_entry",
            notes=f"Manually added entity: {entity_data.title}"
        )
        
        db.add(queue_entry)
        db.commit()
        
        logger.info(f"Manually added entity: {entity_data.title} (QID: {qid})")
        
        return ManualEntityResponse(
            qid=qid,
            title=entity_data.title,
            type=entity_data.type,
            queue_type=entity_data.add_to_queue,
            message=f"Entity '{entity_data.title}' added successfully to {entity_data.add_to_queue.value} queue"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add manual entity: {e}")
        raise HTTPException(status_code=500, detail="Failed to add manual entity")

@router.get("/extraction/queue-stats")
async def get_extraction_queue_stats(db: Session = Depends(get_db)):
    """Get statistics about extraction queues"""
    try:
        from sqlalchemy import func
        
        # Get counts by queue type
        queue_counts = db.query(
            QueueEntry.queue_type,
            func.count(QueueEntry.id).label('count')
        ).group_by(QueueEntry.queue_type).all()
        
        # Get entities ready for extraction (ACTIVE queue)
        ready_for_extraction = db.query(QueueEntry).filter(
            QueueEntry.queue_type == QueueType.ACTIVE.value
        ).count()
        
        # Get entities in review
        in_review = db.query(QueueEntry).filter(
            QueueEntry.queue_type == QueueType.REVIEW.value
        ).count()
        
        # Get processing entities
        processing = db.query(QueueEntry).filter(
            QueueEntry.queue_type == QueueType.PROCESSING.value
        ).count()
        
        return {
            "queue_counts": {stat.queue_type: stat.count for stat in queue_counts},
            "ready_for_extraction": ready_for_extraction,
            "in_review": in_review,
            "currently_processing": processing,
            "extraction_possible": ready_for_extraction > 0 and not extraction_service.is_running
        }
        
    except Exception as e:
        logger.error(f"Failed to get queue stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get queue stats")