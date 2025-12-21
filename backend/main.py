# backend/main.py - UPDATED with extraction service integration
from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime  # Add this import

# Database setup
from database.database import init_database, get_db
from database.models import Entity,UserDecision,QueueEntry

# API routers
from api import entities, queues, analytics, websocket, extraction, files, type_mappings  # NEW: type_mappings

# Services
from services.file_service import FileService
from services.sync_service import SyncService
from services.extraction_service import extraction_service  # NEW


# Ensure logs directory exists
os.makedirs("../logs", exist_ok=True)
# Configure logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/dashboard.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Wikipedia Dashboard API...")

    app.state.startup_time = datetime.utcnow()

    
    # Initialize database
    init_database()
    logger.info("Database initialized")
    
    # Initialize services
    file_service = FileService()
    app.state.file_service = file_service
    app.state.sync_service = SyncService(file_service)
    
    # NEW: Initialize extraction service with WebSocket integration
    app.state.extraction_service = extraction_service
    extraction_service.set_websocket_manager(websocket.manager)
    
    # Perform initial sync if database is empty
    from database.database import SessionLocal
    db = SessionLocal()
    try:
        entity_count = db.query(Entity).count()
        if entity_count == 0:
            logger.info("Database is empty, performing initial sync...")
            stats = app.state.sync_service.sync_database_with_files(db)
            logger.info(f"Initial sync completed: {stats}")
        else:
            logger.info(f"Database already has {entity_count} entities")
    finally:
        db.close()
    
    logger.info("Dashboard API startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Dashboard API...")
    
    # NEW: Cancel any running extraction
    if extraction_service.is_running:
        db = SessionLocal()
        try:
            await extraction_service.cancel_extraction(db)
            logger.info("Active extraction cancelled during shutdown")
        except Exception as e:
            logger.error(f"Error cancelling extraction during shutdown: {e}")
        finally:
            db.close()

# Create FastAPI app
app = FastAPI(
    title="Wikipedia Extraction Dashboard API",
    description="API for managing Wikipedia data extraction pipeline with smart deduplication",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(entities.router, prefix="/api/v1", tags=["entities"])
app.include_router(queues.router, prefix="/api/v1", tags=["queues"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
app.include_router(extraction.router, prefix="/api/v1", tags=["extraction"])  # NEW
app.include_router(files.router, prefix="/api/v1", tags=["files"])
app.include_router(type_mappings.router, prefix="/api/v1", tags=["type-mappings"])  # NEW

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Wikipedia Extraction Dashboard API v2.0",
        "version": "2.0.0",
        "features": [
            "Smart deduplication during link discovery",
            "Real-time extraction monitoring",
            "Manual entity entry",
            "Review queue management",
            "Batch operations with deduplication"
        ],
        "docs": "/docs",
        "websocket": "/api/v1/ws"
    }

# Health check endpoint
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Check database connection
        entity_count = db.query(Entity).count()
        
        # Check file service
        file_stats = app.state.file_service.get_directory_stats()
        
        # Check extraction service status
        extraction_status = extraction_service.get_extraction_status(db)
        
        return {
            "status": "healthy",
            "database": {
                "connected": True,
                "entity_count": entity_count
            },
            "file_system": {
                "accessible": True,
                "total_entities": file_stats.get("total_entities", 0),
                "total_size_mb": round(file_stats.get("total_size_mb", 0), 2)
            },
            "extraction_service": {
                "status": extraction_status.get("status", "idle"),
                "session_id": extraction_status.get("session_id"),
                "current_entity": extraction_status.get("current_entity")
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Add this endpoint to backend/main.py
@app.get("/api/v1/health")
async def get_system_stats(db: Session = Depends(get_db)):
    """Get comprehensive system statistics"""
    try:
        # Database stats
        total_entities = db.query(Entity).count()
        queue_counts = {}
        for queue_type in ["active", "rejected", "on_hold", "completed", "failed", "review", "processing"]:
            count = db.query(QueueEntry).filter(QueueEntry.queue_type == queue_type).count()
            queue_counts[queue_type] = count
        
        # WebSocket stats
        websocket_connections = websocket.manager.get_connection_count()
        
        # File system stats
        file_stats = app.state.file_service.get_directory_stats()
        
        # Extraction service stats
        extraction_status = extraction_service.get_extraction_status(db)
        
        return {
            "database": {
                "total_entities": total_entities,
                "queue_counts": queue_counts,
                "connection_status": "connected"
            },
            "websocket": {
                "active_connections": websocket_connections,
                "status": "operational"
            },
            "file_system": {
                "total_files": file_stats.get("total_entities", 0),
                "total_size_mb": round(file_stats.get("total_size_mb", 0), 2),
                "status": "accessible"
            },
            "extraction_service": {
                "status": extraction_status.get("status", "idle"),
                "current_session": extraction_status.get("session_id"),
                "is_running": extraction_service.is_running
            },
            "system_health": "operational"
        }
    except Exception as e:
        logger.error(f"System stats failed: {e}")
        return {
            "error": str(e),
            "status": "error"
        }

# Manual sync endpoint
@app.post("/api/v1/sync")
async def manual_sync(
    background_tasks: BackgroundTasks,
    full_sync: bool = False,
    db: Session = Depends(get_db)
):
    """Manually trigger database sync with files"""
    try:
        if full_sync:
            # Perform full sync in background
            background_tasks.add_task(perform_full_sync)
            return {
                "message": "Full sync started in background",
                "status": "started"
            }
        else:
            # Perform quick sync
            stats = app.state.sync_service.sync_database_with_files(db)
            return {
                "message": "Sync completed",
                "stats": stats,
                "status": "completed"
            }
    except Exception as e:
        logger.error(f"Manual sync failed: {e}")
        return {
            "message": "Sync failed",
            "error": str(e),
            "status": "failed"
        }

async def perform_full_sync():
    """Perform full synchronization in background"""
    from database.database import SessionLocal
    db = SessionLocal()
    try:
        logger.info("Starting full sync...")
        stats = app.state.sync_service.sync_database_with_files(db)
        logger.info(f"Full sync completed: {stats}")
        
        # Notify WebSocket clients
        await websocket.notify_system_status_change({
            "status": "sync_completed",
            "message": "Database synchronization completed",
            "details": stats
        })
        
    except Exception as e:
        logger.error(f"Full sync failed: {e}")
        await websocket.notify_system_status_change({
            "status": "sync_failed",
            "message": "Database synchronization failed",
            "details": {"error": str(e)}
        })
    finally:
        db.close()

# Validation endpoint
@app.get("/api/v1/validate")
async def validate_system(db: Session = Depends(get_db)):
    """Validate system integrity"""
    try:
        # Validate database-file consistency
        validation_results = app.state.sync_service.validate_database_integrity(db)
        
        return {
            "validation": validation_results,
            "status": "valid" if validation_results["missing_files"] == 0 else "issues_found"
        }
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return {
            "validation": None,
            "error": str(e),
            "status": "error"
        }

# NEW: Pipeline integration endpoints for external extraction pipeline
@app.post("/api/v1/pipeline/entity-extracted")
async def entity_extracted_notification(
    entity_data: dict,
    db: Session = Depends(get_db)
):
    """Called by the extraction pipeline when an entity is extracted"""
    try:
        # Add entity to database
        success = app.state.sync_service.add_entity_from_extraction(db, entity_data)
        
        if success:
            # Notify WebSocket clients
            await websocket.notify_entity_processed(
                entity_data["qid"], 
                entity_data
            )
            
            return {"status": "success", "message": "Entity added to database"}
        else:
            return {"status": "error", "message": "Failed to add entity"}
            
    except Exception as e:
        logger.error(f"Entity extraction notification failed: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/v1/pipeline/progress-update")
async def pipeline_progress_update(progress_data: dict):
    """Called by the extraction pipeline to report progress"""
    try:
        # Notify WebSocket clients
        await websocket.notify_extraction_progress(progress_data)
        
        return {"status": "success", "message": "Progress update sent"}
        
    except Exception as e:
        logger.error(f"Progress update failed: {e}")
        return {"status": "error", "message": str(e)}

# NEW: Deduplication statistics endpoint
@app.get("/api/v1/deduplication/stats")
async def get_deduplication_stats(db: Session = Depends(get_db)):
    """Get smart deduplication statistics"""
    try:
        from utils.schemas import QueueType
        from sqlalchemy import func
        
        # Get counts by decision type for auto decisions
        auto_decisions = db.query(
            UserDecision.decision_value,
            func.count(UserDecision.id).label('count')
        ).filter(
            UserDecision.auto_decision == True,
            UserDecision.decision_type.in_(["skip_duplicate", "discovered_link"])
        ).group_by(UserDecision.decision_value).all()
        
        # Get review queue stats
        review_queue_count = db.query(QueueEntry).filter(
            QueueEntry.queue_type == QueueType.REVIEW.value
        ).count()
        
        # Get discovery sources in review queue
        discovery_sources = db.query(
            QueueEntry.discovery_source,
            func.count(QueueEntry.id).label('count')
        ).filter(
            QueueEntry.queue_type == QueueType.REVIEW.value,
            QueueEntry.discovery_source.isnot(None)
        ).group_by(QueueEntry.discovery_source).all()
        
        return {
            "auto_decisions": {decision.decision_value: decision.count for decision in auto_decisions},
            "review_queue_count": review_queue_count,
            "discovery_sources_count": len(discovery_sources),
            "top_discovery_sources": [
                {"qid": source.discovery_source, "count": source.count}
                for source in discovery_sources[:10]
            ]
        }
        
    except Exception as e:
        logger.error(f"Deduplication stats failed: {e}")
        return {"error": str(e)}

# Statistics endpoints
@app.get("/api/v1/system/stats")
async def get_system_stats(db: Session = Depends(get_db)):
    """Get comprehensive system statistics"""
    try:
        # Database stats
        entity_count = db.query(Entity).count()
        
        # File system stats
        file_stats = app.state.file_service.get_directory_stats()
        
        # WebSocket stats
        ws_stats = {
            "active_connections": websocket.manager.get_connection_count()
        }
        
        # NEW: Extraction service stats
        extraction_status = extraction_service.get_extraction_status(db)
        
        return {
            "database": {
                "total_entities": entity_count,
                "last_updated": "real-time"
            },
            "file_system": file_stats,
            "websocket": ws_stats,
            "extraction": {
                "status": extraction_status.get("status", "idle"),
                "session_id": extraction_status.get("session_id"),
                "progress": extraction_status.get("progress_percentage", 0)
            },
            "system": {
                "status": "operational",
                "uptime": "N/A"  # Could be calculated from startup time
            }
        }
    except Exception as e:
        logger.error(f"System stats failed: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    
    # Create logs directory
    os.makedirs("../logs", exist_ok=True)
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )