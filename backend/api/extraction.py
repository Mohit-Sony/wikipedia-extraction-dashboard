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
import aiohttp
from typing import List, Optional, Dict, Any , Union
from Python_Helper.wiki_extract import extract_wikipedia_page_optimized , APIClient , WikidataAPI

logger = logging.getLogger(__name__)
router = APIRouter()
fileService = FileService()

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
    


async def get_qid_and_type(title: str) -> tuple[Optional[str], Optional[str]]:
    """
    Simple function to get QID and entity type from Wikipedia/Wikidata
    Fetches the actual type label from Wikidata instead of using a mapping
    Returns: (qid, entity_type) or (None, None) if not found
    """
    timeout = aiohttp.ClientTimeout(total=30)
    headers = {
        'User-Agent': 'WikipediaExtractor/2.0 (Educational/Research; Contact: your-email@example.com)'
    }
    
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        try:
            # Step 1: Get QID from Wikipedia API
            wiki_api_url = "https://en.wikipedia.org/w/api.php"
            wiki_params = {
                "action": "query",
                "titles": title,
                "prop": "pageprops",
                "format": "json",
                "redirects": 1
            }
            
            async with session.get(wiki_api_url, params=wiki_params) as response:
                if response.status != 200:
                    logger.warning(f"Wikipedia API returned status {response.status} for {title}")
                    return None, None, None, None

                data = await response.json()
                print(data)

                if not data or 'query' not in data:
                    logger.warning(f"No query data returned for {title}")
                    return None, None, None, None

                pages = data.get("query", {}).get("pages", {})
                if not pages:
                    logger.warning(f"No pages found for {title}")
                    return None, None, None, None

                # Get the first (and should be only) page
                page_info = next(iter(pages.values()))

                # Check if page exists
                if 'missing' in page_info:
                    logger.warning(f"Page not found for {title}")
                    return None, None, None, None

                # Extract QID
                qid = page_info.get("pageprops", {}).get("wikibase_item")
                short_desc = page_info.get("pageprops", {}).get("wikibase-shortdesc")
                query = data.get("query", {})
                redirects = query.get("redirects", [])

                # Build redirect map: original → resolved
                redirect_map = {r["from"]: r["to"] for r in redirects}
                redirect_title = redirect_map.get(title) or title  # only set if it was redirected


                if not qid:
                    logger.warning(f"No QID found for {title}")
                    return None, None, None, None
                
                logger.info(f"Found QID {qid} for {title}")
            
            # Step 2: Get entity type from Wikidata - fetch claims
            wikidata_api_url = "https://www.wikidata.org/w/api.php"
            wikidata_params = {
                "action": "wbgetentities",
                "ids": qid,
                "props": "claims",
                "format": "json"
            }
            
            async with session.get(wikidata_api_url, params=wikidata_params) as response:
                if response.status != 200:
                    logger.warning(f"Wikidata API returned status {response.status} for {qid}")
                    return qid, "unknown"
                
                data = await response.json()
                
                if not data or 'entities' not in data:
                    logger.warning(f"No entities data from Wikidata for {qid}")
                    return qid, "unknown"
                
                entity = data.get("entities", {}).get(qid, {})
                
                if 'missing' in entity:
                    logger.warning(f"Entity missing in Wikidata for {qid}")
                    return qid, "unknown"
                
                # Get instance_of (P31) claim
                claims = entity.get("claims", {})
                instance_of_claims = claims.get("P31", [])
                
                if not instance_of_claims:
                    logger.info(f"No instance_of claims for {qid}")
                    return qid, "unknown"
                
                # Get the first instance_of value
                first_claim = instance_of_claims[0]
                mainsnak = first_claim.get("mainsnak", {})
                datavalue = mainsnak.get("datavalue", {})
                value = datavalue.get("value", {})
                type_qid = value.get("id")
                
                if not type_qid:
                    logger.warning(f"No type QID found in claims for {qid}")
                    return qid, "unknown"
                
                # Step 3: Fetch the actual label for the type QID
                label_params = {
                    "action": "wbgetentities",
                    "ids": type_qid,
                    "props": "labels",
                    "languages": "en",
                    "format": "json"
                }
                
                async with session.get(wikidata_api_url, params=label_params) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch label for type {type_qid}")
                        return qid, "entity" , redirect_title , short_desc
                    
                    label_data = await response.json()
                    
                    if label_data and "entities" in label_data:
                        type_entity = label_data["entities"].get(type_qid, {})
                        label = type_entity.get("labels", {}).get("en", {}).get("value")
                        
                        if label:
                            # Normalize the label: lowercase and replace spaces with underscores
                            entity_type = label.lower().replace(' ', '_')
                            logger.info(f"Resolved type for {qid}: {entity_type} (from {type_qid}: {label})")
                            return qid, entity_type , redirect_title , short_desc
                
                # If we couldn't get the label, return a generic type
                logger.warning(f"Could not fetch label for type {type_qid}")
                return qid, "entity", redirect_title , short_desc
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error resolving '{title}': {e}")
            return None, None, None, None
        except Exception as e:
            logger.error(f"Unexpected error resolving '{title}': {e}")
            return None, None, None, None


@router.post("/entities/manual", response_model=ManualEntityResponse)
async def add_manual_entity(
    entity_data: ManualEntityCreate,
    db: Session = Depends(get_db)
):
    """Manually add entity to the system"""
    try:
        # Generate QID (you might want to use a different strategy)
        # qid = f"Q{abs(hash(entity_data.title)) % 10000000}"
        # qid = "Q5521008"
        resolved_qid, resolved_type , resolved_title , short_desc = await get_qid_and_type(entity_data.title)
        
        # Use resolved values or generate manual ones
        if resolved_qid:
            qid = resolved_qid
            entity_type = resolved_type or entity_data.type
            logger.info(f"Resolved '{entity_data.title}' to QID: {qid}, Type: {entity_type} , resolved_title:   {resolved_title}, short_desc :  {short_desc}")
        else:
            error_msg = f"Could not resolve entity '{entity_data.title}' from Wikipedia/Wikidata"
            logger.error(error_msg)
            raise HTTPException(
                status_code=404,
                detail=f"{error_msg}. Please verify the entity name and try again."
            )
        
        # Check if entity already exists
        existing = db.query(Entity).filter(
            (Entity.qid == qid) | (Entity.title == entity_data.title)
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Entity already exists")
        
        # Create entity
        entity = Entity(
            qid=qid,
            title= resolved_title or entity_data.title,
            type=entity_type,
            short_desc=short_desc or "No data - Manual Entry",
            status="unprocessed",
            file_path=f"wikipedia_data/{entity_type}/{qid}.json",
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