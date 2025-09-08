# backend/api/queues.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database.database import get_db
from database.models import Entity, QueueEntry, UserDecision
from utils.schemas import (
    QueueEntryResponse, QueueEntryCreate, QueueEntryUpdate,
    QueueType, BatchOperation, BatchOperationResult,
    Priority, EntityResponse
)
from typing import List, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/queues", response_model=Dict[str, Any])
async def get_all_queues(db: Session = Depends(get_db)):
    """Get summary of all queues"""
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
                    "priority": entry.priority
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
    db: Session = Depends(get_db)
):
    """Get entities in a specific queue"""
    # Build query
    query = db.query(QueueEntry).join(Entity).filter(
        QueueEntry.queue_type == queue_type.value
    )
    
    # Get total count
    total = query.count()
    
    # Apply sorting
    if sort_by == "title":
        sort_column = Entity.title
    elif sort_by == "priority":
        sort_column = QueueEntry.priority
    elif sort_by == "type":
        sort_column = Entity.type
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
        "has_more": (offset + limit) < total
    }

@router.post("/queues/entries", response_model=QueueEntryResponse)
async def add_to_queue(
    queue_entry: QueueEntryCreate,
    db: Session = Depends(get_db)
):
    """Add entity to a queue"""
    # Check if entity exists
    entity = db.query(Entity).filter(Entity.qid == queue_entry.qid).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Check if already in a queue
    existing_entry = db.query(QueueEntry).filter(QueueEntry.qid == queue_entry.qid).first()
    if existing_entry:
        # Update existing entry
        existing_entry.queue_type = queue_entry.queue_type.value
        existing_entry.priority = queue_entry.priority.value
        existing_entry.notes = queue_entry.notes
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
        added_by="dashboard_user"
    )
    
    # Update entity status
    if queue_entry.queue_type == QueueType.ACTIVE:
        entity.status = "queued"
    elif queue_entry.queue_type == QueueType.REJECTED:
        entity.status = "rejected"
    
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
    """Perform batch operations on multiple entities"""
    results = BatchOperationResult(success_count=0, error_count=0, errors=[])
    
    for qid in operation.qids:
        try:
            if operation.operation == "move":
                success = await _move_entity_to_queue(
                    qid, operation.target_queue, operation.priority, operation.notes, db
                )
            elif operation.operation == "delete":
                success = await _remove_entity_from_queue(qid, db)
            elif operation.operation == "update_priority":
                success = await _update_entity_priority(qid, operation.priority, db)
            else:
                raise ValueError(f"Unknown operation: {operation.operation}")
            
            if success:
                results.success_count += 1
            else:
                results.error_count += 1
                results.errors.append({"qid": qid, "error": "Operation failed"})
                
        except Exception as e:
            results.error_count += 1
            results.errors.append({"qid": qid, "error": str(e)})
    
    db.commit()
    return results

async def _move_entity_to_queue(
    qid: str, 
    target_queue: QueueType, 
    priority: Priority, 
    notes: str, 
    db: Session
) -> bool:
    """Move entity to specified queue"""
    try:
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
        entity = db.query(Entity).filter(Entity.qid == qid).first()
        if entity:
            if target_queue == QueueType.ACTIVE:
                entity.status = "queued"
            elif target_queue == QueueType.REJECTED:
                entity.status = "rejected"
            elif target_queue == QueueType.COMPLETED:
                entity.status = "completed"
        
        # Log decision
        decision = UserDecision(
            qid=qid,
            decision_type="queue_move",
            decision_value=target_queue.value,
            reasoning=f"Batch operation: {notes}" if notes else "Batch operation"
        )
        db.add(decision)
        
        return True
        
    except Exception as e:
        logger.error(f"Error moving entity {qid} to queue: {e}")
        return False

async def _remove_entity_from_queue(qid: str, db: Session) -> bool:
    """Remove entity from all queues"""
    try:
        entries = db.query(QueueEntry).filter(QueueEntry.qid == qid).all()
        for entry in entries:
            db.delete(entry)
        return True
    except Exception as e:
        logger.error(f"Error removing entity {qid} from queue: {e}")
        return False

async def _update_entity_priority(qid: str, priority: Priority, db: Session) -> bool:
    """Update entity priority in queue"""
    try:
        entry = db.query(QueueEntry).filter(QueueEntry.qid == qid).first()
        if entry:
            entry.priority = priority.value
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating priority for entity {qid}: {e}")
        return False

@router.get("/queues/stats/summary")
async def get_queue_stats_summary(db: Session = Depends(get_db)):
    """Get comprehensive queue statistics"""
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
    
    return {
        "queue_counts": {stat.queue_type: stat.count for stat in queue_counts},
        "priority_distribution": {stat.priority: stat.count for stat in priority_dist},
        "type_distribution": {stat.type: stat.count for stat in type_dist}
    }