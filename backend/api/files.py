# backend/api/files.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database.database import get_db
from services.file_service import FileService
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize file service
file_service = FileService()

@router.get("/files/entity/{qid}")
async def get_entity_file(
    qid: str,
    entity_type: str = Query(..., description="Entity type for file location"),
    db: Session = Depends(get_db)
):
    """Get entity file content"""
    try:
        data = file_service.read_entity_data(qid, entity_type)
        if not data:
            raise HTTPException(status_code=404, detail=f"Entity file not found: {qid}")
        return data
    except Exception as e:
        logger.error(f"Error reading entity file {qid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/files/entity/{qid}")
async def delete_entity_file(
    qid: str,
    entity_type: str = Query(..., description="Entity type for file location"),
    db: Session = Depends(get_db)
):
    """Delete entity file"""
    try:
        success = file_service.delete_entity_data(qid, entity_type)
        if not success:
            raise HTTPException(status_code=404, detail=f"Entity file not found: {qid}")
        return {"message": f"Entity file {qid} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting entity file {qid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/check/{qid}")
async def check_entity_file_exists(
    qid: str,
    entity_type: str = Query(..., description="Entity type for file location")
):
    """Check if entity file exists"""
    exists = file_service.entity_file_exists(qid, entity_type)
    return {"qid": qid, "entity_type": entity_type, "file_exists": exists}

@router.get("/files/stats")
async def get_file_stats():
    """Get wikipedia_data directory statistics"""
    try:
        stats = file_service.get_directory_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting file stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/sync")
async def sync_files_with_database(db: Session = Depends(get_db)):
    """Sync files in wikipedia_data with database"""
    try:
        from services.sync_service import SyncService
        sync_service = SyncService(file_service)
        stats = sync_service.sync_database_with_files(db)
        return {
            "message": "Sync completed successfully",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error syncing files with database: {e}")
        raise HTTPException(status_code=500, detail=str(e))