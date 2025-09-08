# backend/utils/schemas.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class QueueType(str, Enum):
    UNPROCESSED = "unprocessed"
    ACTIVE = "active"
    REJECTED = "rejected"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    FAILED = "failed"
    PROCESSING = "processing"

class EntityStatus(str, Enum):
    UNPROCESSED = "unprocessed"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"

class Priority(int, Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3

# Base schemas
class EntityBase(BaseModel):
    qid: str
    title: str
    type: str
    short_desc: Optional[str] = None
    num_links: int = 0
    num_tables: int = 0
    num_images: int = 0
    num_chunks: int = 0
    page_length: int = 0
    parent_qid: Optional[str] = None
    depth: int = 0
    status: EntityStatus = EntityStatus.UNPROCESSED

class EntityCreate(EntityBase):
    file_path: str
    extraction_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None

class EntityUpdate(BaseModel):
    title: Optional[str] = None
    short_desc: Optional[str] = None
    status: Optional[EntityStatus] = None
    num_links: Optional[int] = None
    num_tables: Optional[int] = None
    num_images: Optional[int] = None
    num_chunks: Optional[int] = None
    page_length: Optional[int] = None

class EntityResponse(EntityBase):
    id: int
    file_path: str
    extraction_date: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class EntityPreview(BaseModel):
    qid: str
    title: str
    type: str
    content: Dict[str, Any]
    infobox: Dict[str, Any]
    links: Dict[str, Any]
    metadata: Dict[str, Any]

# Queue schemas
class QueueEntryBase(BaseModel):
    qid: str
    queue_type: QueueType
    priority: Priority = Priority.MEDIUM
    notes: Optional[str] = None

class QueueEntryCreate(QueueEntryBase):
    pass

class QueueEntryUpdate(BaseModel):
    queue_type: Optional[QueueType] = None
    priority: Optional[Priority] = None
    notes: Optional[str] = None

class QueueEntryResponse(QueueEntryBase):
    id: int
    position: int
    added_by: str
    added_date: datetime
    processed_date: Optional[datetime] = None
    entity: EntityResponse
    
    class Config:
        from_attributes = True

# Batch operation schemas
class BatchOperation(BaseModel):
    operation: str  # move, delete, update_priority, update_status
    qids: List[str]
    target_queue: Optional[QueueType] = None
    priority: Optional[Priority] = None
    notes: Optional[str] = None

class BatchOperationResult(BaseModel):
    success_count: int
    error_count: int
    errors: List[Dict[str, str]]

# Filter schemas
class EntityFilter(BaseModel):
    search: Optional[str] = None
    types: Optional[List[str]] = None
    status: Optional[List[EntityStatus]] = None
    queue_type: Optional[List[QueueType]] = None
    parent_qid: Optional[str] = None
    depth_min: Optional[int] = None
    depth_max: Optional[int] = None
    links_min: Optional[int] = None
    links_max: Optional[int] = None
    page_length_min: Optional[int] = None
    page_length_max: Optional[int] = None
    extraction_date_from: Optional[datetime] = None
    extraction_date_to: Optional[datetime] = None
    limit: int = 50
    offset: int = 0
    sort_by: str = "updated_at"
    sort_order: str = "desc"

# Analytics schemas
class QueueStats(BaseModel):
    queue_type: QueueType
    count: int
    avg_links: float
    avg_page_length: float

class TypeStats(BaseModel):
    type: str
    count: int
    avg_links: float
    avg_page_length: float

class DashboardStats(BaseModel):
    total_entities: int
    total_processed: int
    total_pending: int
    total_failed: int
    queue_stats: List[QueueStats]
    type_stats: List[TypeStats]
    recent_activity: List[EntityResponse]

# WebSocket message schemas
class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]

class EntityProcessedMessage(WebSocketMessage):
    type: str = "entity_processed"
    
class QueueUpdatedMessage(WebSocketMessage):
    type: str = "queue_updated"
    
class ExtractionProgressMessage(WebSocketMessage):
    type: str = "extraction_progress"