# backend/api/entities.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from database.database import get_db
from database.models import Entity, QueueEntry
from utils.schemas import (
    EntityResponse, EntityUpdate, EntityFilter, EntityPreview,
    QueueType, EntityStatus
)
from services.file_service import FileService
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
file_service = FileService()

@router.get("/entities", response_model=Dict[str, Any])
async def get_entities(
    search: Optional[str] = Query(None, description="Search in title and description"),
    types: Optional[List[str]] = Query(None, description="Filter by entity types"),
    status: Optional[List[EntityStatus]] = Query(None, description="Filter by status"),
    queue_type: Optional[List[QueueType]] = Query(None, description="Filter by queue type"),
    parent_qid: Optional[str] = Query(None, description="Filter by parent QID"),
    depth_min: Optional[int] = Query(None, description="Minimum depth"),
    depth_max: Optional[int] = Query(None, description="Maximum depth"),
    links_min: Optional[int] = Query(None, description="Minimum number of links"),
    links_max: Optional[int] = Query(None, description="Maximum number of links"),
    page_length_min: Optional[int] = Query(None, description="Minimum page length"),
    page_length_max: Optional[int] = Query(None, description="Maximum page length"),
    limit: int = Query(50, description="Number of results per page"),
    offset: int = Query(0, description="Offset for pagination"),
    sort_by: str = Query("updated_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    db: Session = Depends(get_db)
):
    """Get entities with filtering, sorting, and pagination"""
    try:
        # Build base query
        query = db.query(Entity)
        
        # Join with queue entries if filtering by queue_type
        if queue_type:
            query = query.join(QueueEntry, Entity.qid == QueueEntry.qid)
        
        # Apply filters
        conditions = []
        
        if search:
            search_condition = or_(
                Entity.title.ilike(f"%{search}%"),
                Entity.short_desc.ilike(f"%{search}%"),
                Entity.qid.ilike(f"%{search}%")
            )
            conditions.append(search_condition)
        
        if types:
            conditions.append(Entity.type.in_(types))
        
        if status:
            conditions.append(Entity.status.in_([s.value for s in status]))
        
        if queue_type:
            conditions.append(QueueEntry.queue_type.in_([qt.value for qt in queue_type]))
        
        if parent_qid:
            conditions.append(Entity.parent_qid == parent_qid)
        
        if depth_min is not None:
            conditions.append(Entity.depth >= depth_min)
        
        if depth_max is not None:
            conditions.append(Entity.depth <= depth_max)
        
        if links_min is not None:
            conditions.append(Entity.num_links >= links_min)
        
        if links_max is not None:
            conditions.append(Entity.num_links <= links_max)
        
        if page_length_min is not None:
            conditions.append(Entity.page_length >= page_length_min)
        
        if page_length_max is not None:
            conditions.append(Entity.page_length <= page_length_max)
        
        # Apply conditions
        if conditions:
            query = query.filter(and_(*conditions))
        
        # Get total count for pagination
        total = query.count()
        
        # Apply sorting
        sort_column = getattr(Entity, sort_by, Entity.updated_at)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
        
        # Apply pagination
        entities = query.offset(offset).limit(limit).all()
        
        return {
            "entities": [EntityResponse.from_orm(entity) for entity in entities],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }
        
    except Exception as e:
        logger.error(f"Error getting entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entities/{qid}", response_model=EntityResponse)
async def get_entity(qid: str, db: Session = Depends(get_db)):
    """Get a specific entity by QID"""
    entity = db.query(Entity).filter(Entity.qid == qid).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return EntityResponse.from_orm(entity)

@router.put("/entities/{qid}", response_model=EntityResponse)
async def update_entity(qid: str, entity_update: EntityUpdate, db: Session = Depends(get_db)):
    """Update an entity"""
    entity = db.query(Entity).filter(Entity.qid == qid).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Update only provided fields
    update_data = entity_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entity, field, value)
    
    db.commit()
    db.refresh(entity)
    return EntityResponse.from_orm(entity)

@router.get("/entities/{qid}/preview", response_model=EntityPreview)
async def get_entity_preview(qid: str, db: Session = Depends(get_db)):
    """Get entity preview with content from JSON file"""
    # Get entity from database
    entity = db.query(Entity).filter(Entity.qid == qid).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Get preview data from file
    preview_data = file_service.get_entity_preview(qid, entity.type)
    if not preview_data:
        raise HTTPException(status_code=404, detail="Entity file not found")
    
    return EntityPreview(**preview_data)

@router.get("/entities/{qid}/relationships")
async def get_entity_relationships(qid: str, db: Session = Depends(get_db)):
    """Get entity relationships for network visualization"""
    entity = db.query(Entity).filter(Entity.qid == qid).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    relationships = file_service.get_entity_relationships(qid, entity.type)
    return {"relationships": relationships}

@router.get("/entities/types/stats")
async def get_entity_type_stats(db: Session = Depends(get_db)):
    """Get statistics by entity type"""
    stats = db.query(
        Entity.type,
        func.count(Entity.id).label('count'),
        func.avg(Entity.num_links).label('avg_links'),
        func.avg(Entity.page_length).label('avg_page_length')
    ).group_by(Entity.type).all()
    
    return {
        "type_stats": [
            {
                "type": stat.type,
                "count": stat.count,
                "avg_links": round(stat.avg_links or 0, 2),
                "avg_page_length": round(stat.avg_page_length or 0, 2)
            }
            for stat in stats
        ]
    }

@router.get("/entities/search/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=2),
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db)
):
    """Get search suggestions based on entity titles"""
    suggestions = db.query(Entity.qid, Entity.title, Entity.type).filter(
        Entity.title.ilike(f"%{query}%")
    ).limit(limit).all()
    
    return {
        "suggestions": [
            {"qid": s.qid, "title": s.title, "type": s.type}
            for s in suggestions
        ]
    }