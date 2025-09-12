# backend/api/analytics.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import case, func, desc, extract, and_
from database.database import get_db
from database.models import Entity, QueueEntry, UserDecision, ExtractionSession
from utils.schemas import DashboardStats, QueueStats, TypeStats , EntityResponse
from services.file_service import FileService
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
file_service = FileService()

@router.get("/analytics/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get main dashboard statistics"""
    # Basic counts
    total_entities = db.query(func.count(Entity.id)).scalar()
    total_processed = db.query(func.count(Entity.id)).filter(
        Entity.status.in_(["completed", "processed"])
    ).scalar()
    total_pending = db.query(func.count(QueueEntry.id)).filter(
        QueueEntry.queue_type == "active"
    ).scalar()
    total_failed = db.query(func.count(Entity.id)).filter(
        Entity.status == "failed"
    ).scalar()
    # Before the return statement, add:
    total_in_review = db.query(func.count(Entity.id)).filter(
        Entity.status == "in_review"  # or whatever status represents "in review"
    ).scalar()


    
    # Queue statistics
    queue_stats_raw = db.query(
        QueueEntry.queue_type,
        func.count(QueueEntry.id).label('count'),
        func.avg(Entity.num_links).label('avg_links'),
        func.avg(Entity.page_length).label('avg_page_length')
    ).join(Entity).group_by(QueueEntry.queue_type).all()
    
    queue_stats = [
        QueueStats(
            queue_type=stat.queue_type,
            count=stat.count,
            avg_links=round(stat.avg_links or 0, 2),
            avg_page_length=round(stat.avg_page_length or 0, 2)
        )
        for stat in queue_stats_raw
    ]
    
    # Type statistics
    type_stats_raw = db.query(
        Entity.type,
        func.count(Entity.id).label('count'),
        func.avg(Entity.num_links).label('avg_links'),
        func.avg(Entity.page_length).label('avg_page_length')
    ).group_by(Entity.type).all()
    
    type_stats = [
        TypeStats(
            type=stat.type,
            count=stat.count,
            avg_links=round(stat.avg_links or 0, 2),
            avg_page_length=round(stat.avg_page_length or 0, 2)
        )
        for stat in type_stats_raw
    ]
    
    # Recent activity (last 10 entities)
    recent_entities = db.query(Entity).order_by(
        desc(Entity.updated_at)
    ).limit(10).all()
    
    return DashboardStats(
        total_entities=total_entities,
        total_processed=total_processed,
        total_pending=total_pending,
        total_failed=total_failed,
        total_in_review=total_in_review,  # <-- ADD THIS LINE
        queue_stats=queue_stats,
        type_stats=type_stats,
        recent_activity=[EntityResponse.from_orm(e) for e in recent_entities]
    )

@router.get("/analytics/extraction-trends")
async def get_extraction_trends(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Get extraction trends over time"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Daily extraction counts
    daily_extractions = db.query(
        func.date(Entity.extraction_date).label('date'),
        func.count(Entity.id).label('count')
    ).filter(
        and_(
            Entity.extraction_date >= start_date,
            Entity.extraction_date <= end_date
        )
    ).group_by(func.date(Entity.extraction_date)).order_by('date').all()
    
    # Daily error counts
    daily_errors = db.query(
        func.date(Entity.updated_at).label('date'),
        func.count(Entity.id).label('count')
    ).filter(
        and_(
            Entity.status == "failed",
            Entity.updated_at >= start_date,
            Entity.updated_at <= end_date
        )
    ).group_by(func.date(Entity.updated_at)).order_by('date').all()
    
    return {
        "extractions": [
            {"date": str(stat.date), "count": stat.count}
            for stat in daily_extractions
        ],
        "errors": [
            {"date": str(stat.date), "count": stat.count}
            for stat in daily_errors
        ]
    }

@router.get("/analytics/type-analysis")
async def get_type_analysis(db: Session = Depends(get_db)):
    """Get detailed analysis by entity type"""
    type_analysis = db.query(
        Entity.type,
        func.count(Entity.id).label('total_count'),
        func.sum(case((Entity.status == "completed", 1), else_=0)).label('completed_count'),
        func.sum(case((Entity.status == "failed", 1), else_=0)).label('failed_count'),
        func.avg(Entity.num_links).label('avg_links'),
        func.avg(Entity.num_tables).label('avg_tables'),
        func.avg(Entity.num_images).label('avg_images'),
        func.avg(Entity.page_length).label('avg_page_length'),
        func.max(Entity.num_links).label('max_links'),
        func.min(Entity.num_links).label('min_links')
    ).group_by(Entity.type).all()
    
    return {
        "type_analysis": [
            {
                "type": stat.type,
                "total_count": stat.total_count,
                "completed_count": stat.completed_count or 0,
                "failed_count": stat.failed_count or 0,
                "success_rate": round((stat.completed_count or 0) / stat.total_count * 100, 2) if stat.total_count else 0,
                "avg_links": round(stat.avg_links or 0, 2),
                "avg_tables": round(stat.avg_tables or 0, 2),
                "avg_images": round(stat.avg_images or 0, 2),
                "avg_page_length": round(stat.avg_page_length or 0, 2),
                "max_links": stat.max_links or 0,
                "min_links": stat.min_links or 0
            }
            for stat in type_analysis
        ]
    }
@router.get("/analytics/depth-analysis")
async def get_depth_analysis(db: Session = Depends(get_db)):
    """Analyze extraction by depth levels"""
    depth_analysis = db.query(
        Entity.depth,
        func.count(Entity.id).label('count'),
        func.avg(Entity.num_links).label('avg_links'),
        func.avg(Entity.page_length).label('avg_page_length')
    ).group_by(Entity.depth).order_by(Entity.depth).all()
    
    return {
        "depth_analysis": [
            {
                "depth": stat.depth,
                "count": stat.count,
                "avg_links": round(stat.avg_links or 0, 2),
                "avg_page_length": round(stat.avg_page_length or 0, 2)
            }
            for stat in depth_analysis
        ]
    }

@router.get("/analytics/queue-flow")
async def get_queue_flow_analysis(
    days: int = Query(7, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Analyze how entities flow through queues"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Queue transitions over time
    queue_transitions = db.query(
        func.date(UserDecision.timestamp).label('date'),
        UserDecision.decision_value.label('queue_type'),
        func.count(UserDecision.id).label('count')
    ).filter(
        and_(
            UserDecision.decision_type == "queue_move",
            UserDecision.timestamp >= start_date,
            UserDecision.timestamp <= end_date
        )
    ).group_by(
        func.date(UserDecision.timestamp),
        UserDecision.decision_value
    ).order_by('date').all()
    
    return {
        "queue_transitions": [
            {
                "date": str(transition.date),
                "queue_type": transition.queue_type,
                "count": transition.count
            }
            for transition in queue_transitions
        ]
    }

@router.get("/analytics/user-decisions")
async def get_user_decision_patterns(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Analyze user decision patterns"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Decision type distribution
    decision_types = db.query(
        UserDecision.decision_type,
        func.count(UserDecision.id).label('count')
    ).filter(
        UserDecision.timestamp >= start_date
    ).group_by(UserDecision.decision_type).all()
    
    # Most rejected entity types
    rejected_types = db.query(
        Entity.type,
        func.count(UserDecision.id).label('rejection_count')
    ).join(UserDecision, Entity.qid == UserDecision.qid).filter(
        and_(
            UserDecision.decision_type == "queue_move",
            UserDecision.decision_value == "rejected",
            UserDecision.timestamp >= start_date
        )
    ).group_by(Entity.type).order_by(desc('rejection_count')).all()
    
    # Most approved entity types
    approved_types = db.query(
        Entity.type,
        func.count(UserDecision.id).label('approval_count')
    ).join(UserDecision, Entity.qid == UserDecision.qid).filter(
        and_(
            UserDecision.decision_type == "queue_move",
            UserDecision.decision_value == "active",
            UserDecision.timestamp >= start_date
        )
    ).group_by(Entity.type).order_by(desc('approval_count')).all()
    
    return {
        "decision_types": [
            {"type": dt.decision_type, "count": dt.count}
            for dt in decision_types
        ],
        "most_rejected_types": [
            {"type": rt.type, "count": rt.rejection_count}
            for rt in rejected_types
        ],
        "most_approved_types": [
            {"type": at.type, "count": at.approval_count}
            for at in approved_types
        ]
    }



@router.get("/analytics/content-quality")
async def get_content_quality_metrics(db: Session = Depends(get_db)):
    """Analyze content quality metrics"""
    # Distribution of page lengths
    page_length_dist = db.query(
        case([
            (Entity.page_length < 1000, 'Very Short'),
            (Entity.page_length < 5000, 'Short'),
            (Entity.page_length < 20000, 'Medium'),
            (Entity.page_length < 50000, 'Long'),
        ], else_='Very Long'
        ).label('length_category'),
        func.count(Entity.id).label('count')
    ).group_by('length_category').all()
    
    # Distribution of link counts
    link_count_dist = db.query(
        case(
            whens=[
                (Entity.num_links == 0, 'No Links'),
                (Entity.num_links < 5, 'Few Links'),
                (Entity.num_links < 20, 'Some Links'),
                (Entity.num_links < 50, 'Many Links'),
            ],
            else_='Very Many Links'
        ).label('link_category'),
        func.count(Entity.id).label('count')
    ).group_by('link_category').all()
    
    # Entities with rich content (tables, images, etc.)
    rich_content = db.query(
        func.sum(case((Entity.num_tables > 0, 1), else_=0)).label('with_tables'),
        func.sum(case((Entity.num_images > 0, 1), else_=0)).label('with_images'),
        func.sum(case((Entity.num_chunks > 5, 1), else_=0)).label('well_structured'),
        func.count(Entity.id).label('total')
    ).first()
    
    return {
        "page_length_distribution": [
            {"category": pl.length_category, "count": pl.count}
            for pl in page_length_dist
        ],
        "link_count_distribution": [
            {"category": lc.link_category, "count": lc.count}
            for lc in link_count_dist
        ],
        "content_richness": {
            "entities_with_tables": rich_content.with_tables or 0,
            "entities_with_images": rich_content.with_images or 0,
            "well_structured_entities": rich_content.well_structured or 0,
            "total_entities": rich_content.total,
            "table_percentage": round((rich_content.with_tables or 0) / rich_content.total * 100, 2) if rich_content.total else 0,
            "image_percentage": round((rich_content.with_images or 0) / rich_content.total * 100, 2) if rich_content.total else 0,
            "structure_percentage": round((rich_content.well_structured or 0) / rich_content.total * 100, 2) if rich_content.total else 0
        }
    }


@router.get("/analytics/extraction-performance")
async def get_extraction_performance(
    days: int = Query(7, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """Analyze extraction performance metrics"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Success/failure rates by type
    performance_by_type = db.query(
        Entity.type,
        func.count(Entity.id).label('total'),
        func.sum(func.case([(Entity.status == "completed", 1)], else_=0)).label('success'),
        func.sum(func.case([(Entity.status == "failed", 1)], else_=0)).label('failed')
    ).filter(
        Entity.extraction_date >= start_date
    ).group_by(Entity.type).all()
    
    # Average extraction metrics
    avg_metrics = db.query(
        func.avg(Entity.num_links).label('avg_links'),
        func.avg(Entity.num_tables).label('avg_tables'),
        func.avg(Entity.num_images).label('avg_images'),
        func.avg(Entity.page_length).label('avg_page_length')
    ).filter(
        Entity.extraction_date >= start_date
    ).first()
    
    return {
        "performance_by_type": [
            {
                "type": perf.type,
                "total": perf.total,
                "success": perf.success or 0,
                "failed": perf.failed or 0,
                "success_rate": round((perf.success or 0) / perf.total * 100, 2) if perf.total > 0 else 0
            }
            for perf in performance_by_type
        ],
        "average_metrics": {
            "avg_links": round(avg_metrics.avg_links or 0, 2),
            "avg_tables": round(avg_metrics.avg_tables or 0, 2),
            "avg_images": round(avg_metrics.avg_images or 0, 2),
            "avg_page_length": round(avg_metrics.avg_page_length or 0, 2)
        }
    }

@router.get("/analytics/file-system-stats")
async def get_file_system_stats():
    """Get file system statistics"""
    try:
        stats = file_service.get_directory_stats()
        return {
            "file_system_stats": stats,
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting file system stats: {e}")
        return {"error": "Could not retrieve file system statistics"}

@router.get("/analytics/top-entities")
async def get_top_entities(
    metric: str = Query("num_links", description="Metric to sort by"),
    limit: int = Query(20, description="Number of top entities to return"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    db: Session = Depends(get_db)
):
    """Get top entities by various metrics"""
    query = db.query(Entity)
    
    if entity_type:
        query = query.filter(Entity.type == entity_type)
    
    # Sort by specified metric
    if metric == "num_links":
        query = query.order_by(desc(Entity.num_links))
    elif metric == "num_tables":
        query = query.order_by(desc(Entity.num_tables))
    elif metric == "num_images":
        query = query.order_by(desc(Entity.num_images))
    elif metric == "page_length":
        query = query.order_by(desc(Entity.page_length))
    else:
        query = query.order_by(desc(Entity.num_links))  # default
    
    top_entities = query.limit(limit).all()
    
    return {
        "top_entities": [
            {
                "qid": entity.qid,
                "title": entity.title,
                "type": entity.type,
                "num_links": entity.num_links,
                "num_tables": entity.num_tables,
                "num_images": entity.num_images,
                "page_length": entity.page_length,
                metric: getattr(entity, metric)
            }
            for entity in top_entities
        ],
        "metric": metric,
        "entity_type": entity_type
    }