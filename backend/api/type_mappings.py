# backend/api/type_mappings.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from services.type_filter_service import TypeFilterService
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Schemas
class TypeMappingCreate(BaseModel):
    wikidata_type: str
    mapped_type: str
    wikidata_qid: Optional[str] = None
    is_approved: bool = True
    source: str = "manual"
    created_by: str = "admin"
    notes: Optional[str] = None

class TypeMappingUpdate(BaseModel):
    mapped_type: Optional[str] = None
    wikidata_qid: Optional[str] = None
    is_approved: Optional[bool] = None
    notes: Optional[str] = None

class TypeMappingResponse(BaseModel):
    id: int
    wikidata_type: str
    wikidata_qid: Optional[str] = None
    mapped_type: str
    is_approved: bool
    confidence: float = 1.0
    source: str = "manual"
    created_by: str = "admin"
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class TypeFilterRequest(BaseModel):
    qids: List[str]

class TypeFilterResponse(BaseModel):
    approved: List[str]
    rejected: List[str]
    unmapped_types: List[str]

class UnmappedTypeInfo(BaseModel):
    type: str
    count: int
    example_qids: List[Dict[str, str]]

class BulkTypeMappingRequest(BaseModel):
    mappings: List[TypeMappingCreate]
    fail_on_error: bool = False

class BulkTypeMappingResponse(BaseModel):
    success: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    total: int
    success_count: int
    error_count: int

# Endpoints

@router.get("/type-mappings", response_model=List[TypeMappingResponse])
async def get_all_type_mappings(
    approved_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all type mappings"""
    try:
        service = TypeFilterService(db)
        mappings = service.get_all_type_mappings(approved_only=approved_only)
        return mappings
    except Exception as e:
        logger.error(f"Failed to get type mappings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get type mappings")

@router.post("/type-mappings", response_model=TypeMappingResponse)
async def create_type_mapping(
    mapping_data: TypeMappingCreate,
    db: Session = Depends(get_db)
):
    """Create a new type mapping"""
    try:
        # Validate mapped_type
        valid_types = {"person", "location", "event", "dynasty", "political_entity", "timeline", "other"}
        if mapping_data.mapped_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mapped_type. Must be one of: {', '.join(valid_types)}"
            )

        service = TypeFilterService(db)
        mapping = service.create_type_mapping(
            wikidata_type=mapping_data.wikidata_type,
            mapped_type=mapping_data.mapped_type,
            wikidata_qid=mapping_data.wikidata_qid,
            is_approved=mapping_data.is_approved,
            source=mapping_data.source,
            created_by=mapping_data.created_by,
            notes=mapping_data.notes
        )
        return mapping
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create type mapping: {e}")
        raise HTTPException(status_code=500, detail="Failed to create type mapping")

@router.put("/type-mappings/{mapping_id}", response_model=TypeMappingResponse)
async def update_type_mapping(
    mapping_id: int,
    update_data: TypeMappingUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing type mapping"""
    try:
        from database.models import TypeMapping

        mapping = db.query(TypeMapping).filter(TypeMapping.id == mapping_id).first()
        if not mapping:
            raise HTTPException(status_code=404, detail="Type mapping not found")

        # Update fields
        if update_data.mapped_type is not None:
            valid_types = {"person", "location", "event", "dynasty", "political_entity", "timeline", "other"}
            if update_data.mapped_type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid mapped_type. Must be one of: {', '.join(valid_types)}"
                )
            mapping.mapped_type = update_data.mapped_type

        if update_data.wikidata_qid is not None:
            mapping.wikidata_qid = update_data.wikidata_qid

        if update_data.is_approved is not None:
            mapping.is_approved = update_data.is_approved

        if update_data.notes is not None:
            mapping.notes = update_data.notes

        db.commit()
        db.refresh(mapping)
        return mapping

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update type mapping: {e}")
        raise HTTPException(status_code=500, detail="Failed to update type mapping")

@router.delete("/type-mappings/{mapping_id}")
async def delete_type_mapping(
    mapping_id: int,
    db: Session = Depends(get_db)
):
    """Delete a type mapping"""
    try:
        service = TypeFilterService(db)
        success = service.delete_type_mapping(mapping_id)

        if not success:
            raise HTTPException(status_code=404, detail="Type mapping not found")

        return {"message": "Type mapping deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete type mapping: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete type mapping")

@router.post("/type-mappings/filter", response_model=TypeFilterResponse)
async def filter_by_type(
    request: TypeFilterRequest,
    db: Session = Depends(get_db)
):
    """Filter entities by approved types"""
    try:
        service = TypeFilterService(db)
        result = service.filter_entities_by_approved_types(request.qids)
        return result

    except Exception as e:
        logger.error(f"Failed to filter by type: {e}")
        raise HTTPException(status_code=500, detail="Failed to filter by type")

@router.get("/type-mappings/unmapped", response_model=List[UnmappedTypeInfo])
async def get_unmapped_types(db: Session = Depends(get_db)):
    """Get all unmapped types currently in review queue"""
    try:
        service = TypeFilterService(db)
        unmapped_types = service.get_unmapped_types_in_review_queue()
        return unmapped_types

    except Exception as e:
        logger.error(f"Failed to get unmapped types: {e}")
        raise HTTPException(status_code=500, detail="Failed to get unmapped types")

@router.get("/type-mappings/approved-types")
async def get_approved_types():
    """Get list of approved standard types"""
    return {
        "approved_types": [
            "person",
            "location",
            "event",
            "dynasty",
            "political_entity",
            "timeline",
            "other"
        ]
    }

@router.post("/type-mappings/bulk", response_model=BulkTypeMappingResponse)
async def bulk_create_type_mappings(
    request: BulkTypeMappingRequest,
    db: Session = Depends(get_db)
):
    """Create multiple type mappings at once"""
    try:
        service = TypeFilterService(db)

        # Convert Pydantic models to dicts
        mappings_data = [mapping.dict() for mapping in request.mappings]

        # Bulk create
        result = service.bulk_create_type_mappings(
            mappings_data=mappings_data,
            fail_on_error=request.fail_on_error
        )

        return result

    except Exception as e:
        logger.error(f"Failed to bulk create type mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
