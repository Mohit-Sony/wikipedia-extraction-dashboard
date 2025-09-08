# backend/api/queues.py - UPDATED with smart deduplication
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from database.database import get_db
from database.models import Entity, QueueEntry, UserDecision
from utils.schemas import (
    QueueEntryResponse, QueueEntryCreate, QueueEntryUpdate,
    QueueType, BatchOperation, BatchOperationResult,
    Priority, EntityResponse
)
from services.extraction_service import SmartDeduplicationService
from typing import List, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/queues", response_model=Dict[str, Any])
async def get_all_queues(db: Session = Depends(get_db)):
    """Get summary of all queues including new REVIEW queue"""
    queue_stats = db.query(
        QueueEntry.queue_type,
        func.count(QueueEntry.id).label('count')
    ).group_by(QueueEntry.queue_type).all()
    
    # Get recent additions for each queue
    queues_data = {}
    for queue_type in QueueType:
        count = next((stat.count for stat in queue_stats if stat.queue_type == queue_type.value), 0)
        
        # Get recent entries
        recent_entries = db.query(QueueEntry).join(Entity).filter(
            QueueEntry.queue_type == queue_type.value
        ).order_by(desc(QueueEntry.added_date)).limit(5).all()
        
        queues_data[queue_type.value] = {
            "count": count,
            "recent_entries": [
                {
                    "qid": entry.qid,
                    "title": entry.entity.title,
                    "type": entry.entity.type,
                    "added_date": entry.added_date,
                    "priority": entry.priority,
                    "discovery_source": entry.discovery_source,  # NEW
                    "discovered_by": entry.entity.discovered_by  # NEW
                }
                for entry in recent_entries
            ]
        }
    
    return queues_data

@router.get("/queues/{queue_type}", response_model=Dict[str, Any])
async def get_queue_entities(
    queue_type: QueueType,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "added_date",
    sort_order: str = "desc",
    discovery_source: str = None,  # NEW - Filter by discovery source
    db: Session = Depends(get_db)
):
    """Get entities in a specific queue with enhanced filtering"""
    # Build query
    query = db.query(QueueEntry).join(Entity).filter(
        QueueEntry.queue_type == queue_type.value
    )
    
    # Filter by discovery source if specified
    if discovery_source:
        query = query.filter(QueueEntry.discovery_source == discovery_source)
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    if sort_by == "title":
        sort_column = Entity.title
    elif sort_by == "priority":
        sort_column = QueueEntry.priority
    elif sort_by == "type":
        sort_column = Entity.type
    elif sort_by == "discovery_source":
        sort_column = QueueEntry.discovery_source
    elif sort_by == "depth":
        sort_column = Entity.depth
    else:
        sort_column = QueueEntry.added_date
    
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)
    
    # Apply pagination
    entries = query.offset(offset).limit(limit).all()
    
    return {
        "queue_type": queue_type.value,
        "entries": [QueueEntryResponse.from_orm(entry) for entry in entries],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
        "discovery_sources": _get_discovery_sources(db, queue_type) if queue_type == QueueType.REVIEW else []
    }

def _get_discovery_sources(db: Session, queue_type: QueueType) -> List[Dict[str, Any]]:
    """Get unique discovery sources for a queue"""
    sources = db.query(
        QueueEntry.discovery_source,
        Entity.title,
        func.count(QueueEntry.id).label('count')
    ).join(Entity, QueueEntry.discovery_source == Entity.qid).filter(
        QueueEntry.queue_type == queue_type.value,
        QueueEntry.discovery_source.isnot(None)
    ).group_by(QueueEntry.discovery_source, Entity.title).all()
    
    return [
        {
            "qid": source.discovery_source,
            "title": source.title,
            "count": source.count
        }
        for source in sources
    ]

@router.post("/queues/entries", response_model=QueueEntryResponse)
async def add_to_queue(
    queue_entry: QueueEntryCreate,
    db: Session = Depends(get_db)
):
    """Add entity to a queue with smart deduplication check"""
    # Check if entity exists
    entity = db.query(Entity).filter(Entity.qid == queue_entry.qid).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Smart deduplication check
    dedup_service = SmartDeduplicationService(db)
    check_result = dedup_service.check_entity_status(queue_entry.qid, entity.title)
    
    if not check_result['should_add'] and queue_entry.queue_type not in [QueueType.REJECTED, QueueType.COMPLETED]:
        raise HTTPException(
            status_code=400, 
            detail=f"Entity already processed: {check_result['reason']} (status: {check_result['existing_status']})"
        )
    
    # Check if already in a queue
    existing_entry = db.query(QueueEntry).filter(QueueEntry.qid == queue_entry.qid).first()
    if existing_entry:
        # Update existing entry
        existing_entry.queue_type = queue_entry.queue_type.value
        existing_entry.priority = queue_entry.priority.value
        existing_entry.notes = queue_entry.notes
        existing_entry.discovery_source = queue_entry.discovery_source
        existing_entry.added_date = datetime.utcnow()
        db.commit()
        db.refresh(existing_entry)
        return QueueEntryResponse.from_orm(existing_entry)
    
    # Create new queue entry
    new_entry = QueueEntry(
        qid=queue_entry.qid,
        queue_type=queue_entry.queue_type.value,
        priority=queue_entry.priority.value,
        notes=queue_entry.notes,
        discovery_source=queue_entry.discovery_source,
        added_by="dashboard_user"
    )
    
    # Update entity status
    if queue_entry.queue_type == QueueType.ACTIVE:
        entity.status = "queued"
    elif queue_entry.queue_type == QueueType.REJECTED:
        entity.status = "rejected"
    elif queue_entry.queue_type == QueueType.REVIEW:
        entity.status = "unprocessed"
    
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    
    return QueueEntryResponse.from_orm(new_entry)

@router.put("/queues/entries/{entry_id}", response_model=QueueEntryResponse)
async def update_queue_entry(
    entry_id: int,
    update_data: QueueEntryUpdate,
    db: Session = Depends(get_db)
):
    """Update a queue entry"""
    entry = db.query(QueueEntry).filter(QueueEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    
    # Update fields
    update_fields = update_data.dict(exclude_unset=True)
    for field, value in update_fields.items():
        if field == "queue_type" and value:
            setattr(entry, field, value.value)
        elif field == "priority" and value:
            setattr(entry, field, value.value)
        else:
            setattr(entry, field, value)
    
    db.commit()
    db.refresh(entry)
    return QueueEntryResponse.from_orm(entry)

@router.delete("/queues/entries/{entry_id}")
async def remove_from_queue(entry_id: int, db: Session = Depends(get_db)):
    """Remove entity from queue"""
    entry = db.query(QueueEntry).filter(QueueEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    
    db.delete(entry)
    db.commit()
    return {"message": "Entity removed from queue"}

@router.post("/queues/batch", response_model=BatchOperationResult)
async def batch_queue_operation(
    operation: BatchOperation,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Perform batch operations on multiple entities with smart deduplication"""
    results = BatchOperationResult(success_count=0, error_count=0, skipped_count=0, errors=[])
    dedup_service = SmartDeduplicationService(db)
    
    for qid in operation.qids:
        try:
            if operation.operation == "move":
                success, skipped = await _move_entity_to_queue_with_dedup(
                    qid, operation.target_queue, operation.priority, operation.notes, db, dedup_service
                )
            elif operation.operation == "delete":
                success, skipped = await _remove_entity_from_queue(qid, db)
            elif operation.operation == "update_priority":
                success, skipped = await _update_entity_priority(qid, operation.priority, db)
            elif operation.operation == "approve_review":  # NEW - Move from REVIEW to ACTIVE
                success, skipped = await _move_entity_to_queue_with_dedup(
                    qid, QueueType.ACTIVE, operation.priority, "Approved from review", db, dedup_service
                )
            elif operation.operation == "reject_review":  # NEW - Move from REVIEW to REJECTED
                success, skipped = await _move_entity_to_queue_with_dedup(
                    qid, QueueType.REJECTED, operation.priority, "Rejected from review", db, dedup_service
                )
            else:
                raise ValueError(f"Unknown operation: {operation.operation}")
            
            if skipped:
                results.skipped_count += 1
                results.errors.append({"qid": qid, "error": "Skipped due to deduplication"})
            elif success:
                results.success_count += 1
            else:
                results.error_count += 1
                results.errors.append({"qid": qid, "error": "Operation failed"})
                
        except Exception as e:
            results.error_count += 1
            results.errors.append({"qid": qid, "error": str(e)})
    
    db.commit()
    return results

async def _move_entity_to_queue_with_dedup(
    qid: str, 
    target_queue: QueueType, 
    priority: Priority, 
    notes: str, 
    db: Session,
    dedup_service: SmartDeduplicationService
) -> tuple[bool, bool]:  # (success, skipped)
    """Move entity to specified queue with deduplication check"""
    try:
        # Get entity
        entity = db.query(Entity).filter(Entity.qid == qid).first()
        if not entity:
            return False, False
        
        # Check deduplication only for certain target queues
        if target_queue in [QueueType.ACTIVE, QueueType.REVIEW]:
            check_result = dedup_service.check_entity_status(qid, entity.title)
            if not check_result['should_add']:
                # Log the skip decision
                decision = UserDecision(
                    qid=qid,
                    decision_type="batch_skip",
                    decision_value=check_result['reason'],
                    reasoning=f"Skipped batch operation: {check_result['reason']}",
                    auto_decision=True
                )
                db.add(decision)
                return False, True  # Skipped
        
        # Get or create queue entry
        entry = db.query(QueueEntry).filter(QueueEntry.qid == qid).first()
        
        if entry:
            entry.queue_type = target_queue.value
            entry.priority = priority.value if priority else entry.priority
            entry.notes = notes or entry.notes
            entry.added_date = datetime.utcnow()
        else:
            # Create new entry
            entry = QueueEntry(
                qid=qid,
                queue_type=target_queue.value,
                priority=priority.value if priority else Priority.MEDIUM.value,
                notes=notes,
                added_by="batch_operation"
            )
            db.add(entry)
        
        # Update entity status
        if target_queue == QueueType.ACTIVE:
            entity.status = "queued"
        elif target_queue == QueueType.REJECTED:
            entity.status = "rejected"
        elif target_queue == QueueType.COMPLETED:
            entity.status = "completed"
        elif target_queue == QueueType.REVIEW:
            entity.status = "unprocessed"
        
        # Log decision
        decision = UserDecision(
            qid=qid,
            decision_type="queue_move",
            decision_value=target_queue.value,
            reasoning=f"Batch operation: {notes}" if notes else "Batch operation"
        )
        db.add(decision)
        
        return True, False
        
    except Exception as e:
        logger.error(f"Error moving entity {qid} to queue: {e}")
        return False, False

async def _remove_entity_from_queue(qid: str, db: Session) -> tuple[bool, bool]:
    """Remove entity from all queues"""
    try:
        entries = db.query(QueueEntry).filter(QueueEntry.qid == qid).all()
        for entry in entries:
            db.delete(entry)
        return True, False
    except Exception as e:
        logger.error(f"Error removing entity {qid} from queue: {e}")
        return False, False

async def _update_entity_priority(qid: str, priority: Priority, db: Session) -> tuple[bool, bool]:
    """Update entity priority in queue"""
    try:
        entry = db.query(QueueEntry).filter(QueueEntry.qid == qid).first()
        if entry:
            entry.priority = priority.value
            return True, False
        return False, False
    except Exception as e:
        logger.error(f"Error updating priority for entity {qid}: {e}")
        return False, False

@router.get("/queues/stats/summary")
async def get_queue_stats_summary(db: Session = Depends(get_db)):
    """Get comprehensive queue statistics including REVIEW queue"""
    # Basic queue counts
    queue_counts = db.query(
        QueueEntry.queue_type,
        func.count(QueueEntry.id).label('count')
    ).group_by(QueueEntry.queue_type).all()
    
    # Priority distribution in active queue
    priority_dist = db.query(
        QueueEntry.priority,
        func.count(QueueEntry.id).label('count')
    ).filter(QueueEntry.queue_type == QueueType.ACTIVE.value).group_by(QueueEntry.priority).all()
    
    # Type distribution in active queue
    type_dist = db.query(
        Entity.type,
        func.count(QueueEntry.id).label('count')
    ).join(QueueEntry).filter(
        QueueEntry.queue_type == QueueType.ACTIVE.value
    ).group_by(Entity.type).all()
    
    # NEW: Discovery source stats for review queue
    discovery_stats = db.query(
        QueueEntry.discovery_source,
        Entity.title,
        func.count(QueueEntry.id).label('count')
    ).join(Entity, QueueEntry.discovery_source == Entity.qid).filter(
        QueueEntry.queue_type == QueueType.REVIEW.value,
        QueueEntry.discovery_source.isnot(None)
    ).group_by(QueueEntry.discovery_source, Entity.title).all()
    
    # NEW: Depth distribution in review queue
    depth_dist = db.query(
        Entity.depth,
        func.count(QueueEntry.id).label('count')
    ).join(QueueEntry).filter(
        QueueEntry.queue_type == QueueType.REVIEW.value
    ).group_by(Entity.depth).all()
    
    return {
        "queue_counts": {stat.queue_type: stat.count for stat in queue_counts},
        "priority_distribution": {stat.priority: stat.count for stat in priority_dist},
        "type_distribution": {stat.type: stat.count for stat in type_dist},
        "discovery_sources": [
            {
                "source_qid": stat.discovery_source,
                "source_title": stat.title,
                "discovered_count": stat.count
            }
            for stat in discovery_stats
        ],
        "depth_distribution": {stat.depth: stat.count for stat in depth_dist}
    }

@router.get("/queues/review/sources")
async def get_review_queue_sources(db: Session = Depends(get_db)):
    """Get discovery sources for review queue with detailed stats"""
    sources = db.query(
        QueueEntry.discovery_source,
        Entity.title,
        Entity.type,
        func.count(QueueEntry.id).label('discovered_count'),
        func.max(QueueEntry.added_date).label('last_discovery')
    ).join(Entity, QueueEntry.discovery_source == Entity.qid).filter(
        QueueEntry.queue_type == QueueType.REVIEW.value,
        QueueEntry.discovery_source.isnot(None)
    ).group_by(
        QueueEntry.discovery_source, Entity.title, Entity.type
    ).order_by(desc('last_discovery')).all()
    
    return {
        "sources": [
            {
                "qid": source.discovery_source,
                "title": source.title,
                "type": source.type,
                "discovered_count": source.discovered_count,
                "last_discovery": source.last_discovery
            }
            for source in sources
        ]
    }

@router.post("/queues/review/bulk-approve")
async def bulk_approve_review_entities(
    source_qid: str = None,
    entity_type: str = None,
    limit: int = None,
    db: Session = Depends(get_db)
):
    """Bulk approve entities from review queue based on criteria"""
    try:
        # Build query for entities to approve
        query = db.query(QueueEntry).join(Entity).filter(
            QueueEntry.queue_type == QueueType.REVIEW.value
        )
        
        if source_qid:
            query = query.filter(QueueEntry.discovery_source == source_qid)
        
        if entity_type:
            query = query.filter(Entity.type == entity_type)
        
        if limit:
            query = query.limit(limit)
        
        entries_to_approve = query.all()
        
        if not entries_to_approve:
            return {"message": "No entities found matching criteria", "approved_count": 0}
        
        # Move to active queue
        approved_count = 0
        dedup_service = SmartDeduplicationService(db)
        
        for entry in entries_to_approve:
            # Check deduplication
            check_result = dedup_service.check_entity_status(entry.qid, entry.entity.title)
            
            if check_result['should_add']:
                entry.queue_type = QueueType.ACTIVE.value
                entry.entity.status = "queued"
                entry.added_date = datetime.utcnow()
                entry.notes = f"Bulk approved from review queue"
                
                # Log decision
                decision = UserDecision(
                    qid=entry.qid,
                    decision_type="bulk_approve",
                    decision_value="moved_to_active",
                    reasoning=f"Bulk approved from review queue (source: {source_qid}, type: {entity_type})"
                )
                db.add(decision)
                
                approved_count += 1
        
        db.commit()
        
        return {
            "message": f"Bulk approval completed",
            "approved_count": approved_count,
            "total_found": len(entries_to_approve),
            "skipped_duplicates": len(entries_to_approve) - approved_count
        }
        
    except Exception as e:
        logger.error(f"Bulk approve failed: {e}")
        raise HTTPException(status_code=500, detail="Bulk approve operation failed")

@router.post("/queues/review/bulk-reject")
async def bulk_reject_review_entities(
    source_qid: str = None,
    entity_type: str = None,
    limit: int = None,
    db: Session = Depends(get_db)
):
    """Bulk reject entities from review queue based on criteria"""
    try:
        # Build query for entities to reject
        query = db.query(QueueEntry).join(Entity).filter(
            QueueEntry.queue_type == QueueType.REVIEW.value
        )
        
        if source_qid:
            query = query.filter(QueueEntry.discovery_source == source_qid)
        
        if entity_type:
            query = query.filter(Entity.type == entity_type)
        
        if limit:
            query = query.limit(limit)
        
        entries_to_reject = query.all()
        
        if not entries_to_reject:
            return {"message": "No entities found matching criteria", "rejected_count": 0}
        
        # Move to rejected queue
        rejected_count = 0
        
        for entry in entries_to_reject:
            entry.queue_type = QueueType.REJECTED.value
            entry.entity.status = "rejected"
            entry.added_date = datetime.utcnow()
            entry.notes = f"Bulk rejected from review queue"
            
            # Log decision
            decision = UserDecision(
                qid=entry.qid,
                decision_type="bulk_reject",
                decision_value="moved_to_rejected",
                reasoning=f"Bulk rejected from review queue (source: {source_qid}, type: {entity_type})"
            )
            db.add(decision)
            
            rejected_count += 1
        
        db.commit()
        
        return {
            "message": f"Bulk rejection completed",
            "rejected_count": rejected_count,
            "total_found": len(entries_to_reject)
        }
        
    except Exception as e:
        logger.error(f"Bulk reject failed: {e}")
        raise HTTPException(status_code=500, detail="Bulk reject operation failed")