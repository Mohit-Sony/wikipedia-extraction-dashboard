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

# backend/api/entities.py - ENHANCED PREVIEW ENDPOINT


@router.get("/entities/{qid}/preview")
async def get_entity_preview(qid: str, db: Session = Depends(get_db)):
    """Get enhanced entity preview with comprehensive data matching frontend EntityPreview interface"""
    # Get entity from database
    entity = db.query(Entity).filter(Entity.qid == qid).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # Get full entity data from file
    entity_data = file_service.read_entity_data(qid, entity.type)
    if not entity_data:
        raise HTTPException(status_code=404, detail="Entity file not found")
    
    # Extract data from JSON structure
    content = entity_data.get('content', {})
    links = entity_data.get('links', {})
    internal_links = links.get('internal_links', [])
    external_links = links.get('external_links', [])
    tables = entity_data.get('tables', [])
    images = entity_data.get('images', [])
    metadata = entity_data.get('metadata', {})
    extraction_metadata = entity_data.get('extraction_metadata', {})
    chunks = entity_data.get('chunks', [])
    categories = entity_data.get('categories', [])
    infobox = entity_data.get('infobox', {})
    
    # Get entity relationships from database
    children_count = db.query(Entity).filter(Entity.parent_qid == qid).count()
    same_depth_count = db.query(Entity).filter(
        Entity.depth == entity.depth,
        Entity.qid != qid
    ).count() if entity.depth > 0 else 0
    
    # Get queue status
    queue_entry = db.query(QueueEntry).filter(QueueEntry.qid == qid).first()
    queue_status = {
        "queue_type": queue_entry.queue_type if queue_entry else "none",
        "priority": queue_entry.priority if queue_entry else None,
        "notes": queue_entry.notes if queue_entry else None
    }
    
    # Build response matching exact frontend interface structure
    preview_response = {
        "qid": qid,
        "title": entity_data.get('title', ''),
        "type": entity.type,
        
        # Content structure - exactly matching frontend interface
        "content": {
            "description": content.get('description', ''),
            "extract": content.get('extract', ''),
            "wikitext_preview": content.get('wikitext', '')[:1000] if content.get('wikitext') else None
        },
        
        # Content chunks - matching frontend structure
        "content_chunks": [
            {
                "section": chunk.get('section', ''),
                "paragraph": chunk.get('paragraph', 0),
                "text_preview": chunk.get('chunk_text', '')[:200],
                "has_references": len(chunk.get('references', [])) > 0
            }
            for chunk in chunks[:15]  # First 15 chunks
        ],
        
        # Images - matching frontend structure
        "images": [
            {
                "index": i,
                "url": image.get('url', ''),
                "alt": image.get('alt', ''),
                "caption": image.get('caption', '') if image.get('caption') else None,
                "filename": image.get('filename', '') if image.get('filename') else None
            }
            for i, image in enumerate(images[:10])  # First 10 images
        ],
        
        # Tables - matching frontend structure
        "tables": [
            {
                "index": i,
                "caption": table.get('caption', f'Table {i+1}'),
                "headers": table.get('headers', [])[:10],  # First 10 headers
                "sample_rows": table.get('rows', [])[:5],  # First 5 rows
                "total_rows": len(table.get('rows', [])),
                "total_columns": len(table.get('headers', []))
            }
            for i, table in enumerate(tables[:8])  # First 8 tables
        ],
        
        # Metadata - matching frontend structure
        "metadata": {
            "page_length": metadata.get('page_length', 0),
            "page_id": str(metadata.get('page_id', '')),
            "revision_id": str(metadata.get('revId', '')),
            "last_modified": metadata.get('last_modified'),
            "num_tables": len(tables),
            "num_images": len(images),
            "num_chunks": len(chunks),
            "num_references": len(entity_data.get('references', [])),
            "num_categories": len(categories)
        },
        
        # Links - matching frontend structure
        "links": {
            "internal_count": len(internal_links),
            "external_count": len(external_links),
            "internal_links": [
                {
                    "qid": link.get('qid', ''),
                    "title": link.get('title', ''),
                    "type": link.get('type', 'unknown'),
                    "shortDesc": link.get('shortDesc') if link.get('shortDesc') else None
                }
                for link in internal_links[:20]  # First 20 internal links
            ],
            "external_links": [
                {
                    "title": link.get('title', ''),
                    "url": link.get('url', '')
                }
                for link in external_links[:10]  # First 10 external links
            ],
            "top_link_types": _get_link_type_distribution(internal_links)
        },
        
        # Infobox - ensuring all values are string/number/boolean
        "infobox": {
            key: _convert_infobox_value(value) 
            for key, value in infobox.items()
        },
        
        # Categories - simple array of strings
        "categories": categories[:25],  # First 25 categories
        
        # Extraction info - matching frontend structure
        "extraction_info": {
            "timestamp": extraction_metadata.get('timestamp', ''),
            "extraction_time": float(extraction_metadata.get('extraction_time', 0)),
            "depth": int(extraction_metadata.get('depth', 0)),
            "parent_qid": extraction_metadata.get('parent_qid') if extraction_metadata.get('parent_qid') else None,
            "extractor_version": extraction_metadata.get('extractor_version', '')
        },
        
        # Relationships - matching frontend structure
        "relationships": {
            "children_count": children_count,
            "same_depth_count": same_depth_count,
            "queue_status": queue_status
        }
    }
    
    return preview_response



def _get_link_type_distribution(internal_links: List[Dict]) -> List[Dict]:
    """Analyze distribution of link types"""
    type_counts = {}
    for link in internal_links:
        link_type = link.get('type', 'unknown')
        type_counts[link_type] = type_counts.get(link_type, 0) + 1
    
    # Return top 5 types
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    return [{'type': t, 'count': c} for t, c in sorted_types[:5]]


def _get_entity_queue_status(qid: str, db: Session) -> Dict:
    """Get current queue status for entity"""
    queue_entry = db.query(QueueEntry).filter(QueueEntry.qid == qid).first()
    if not queue_entry:
        return {'queue_type': None, 'priority': None, 'added_date': None}
    
    return {
        'queue_type': queue_entry.queue_type,
        'priority': queue_entry.priority,
        'added_date': queue_entry.added_date.isoformat() if queue_entry.added_date else None,
        'notes': queue_entry.notes
    }

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