# backend/main.py
from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import logging
import os
from contextlib import asynccontextmanager

# Database setup
from database.database import init_database, get_db
from database.models import Entity

# API routers
from api import entities, queues, analytics, websocket

# Services
from services.file_service import FileService
from services.sync_service import SyncService

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
    
    # Initialize database
    init_database()
    logger.info("Database initialized")
    
    # Initialize services
    file_service = FileService()
    app.state.file_service = file_service
    app.state.sync_service = SyncService(file_service)
    
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

# Create FastAPI app
app = FastAPI(
    title="Wikipedia Extraction Dashboard API",
    description="API for managing Wikipedia data extraction pipeline",
    version="1.0.0",
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

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Wikipedia Extraction Dashboard API",
        "version": "1.0.0",
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
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
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

# Pipeline integration endpoints
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
        
        return {
            "database": {
                "total_entities": entity_count,
                "last_updated": "real-time"
            },
            "file_system": file_stats,
            "websocket": ws_stats,
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
        port=8000,
        reload=True,
        log_level="info"
    )