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
    REVIEW = "review"  # NEW - For discovered links awaiting decision

class EntityStatus(str, Enum):
    UNPROCESSED = "unprocessed"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"

class ExtractionStatus(str, Enum):  # NEW
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"

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
    discovered_by: Optional[str] = None  # NEW

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

# Manual Entity Entry Schemas - NEW
class ManualEntityCreate(BaseModel):
    title: str
    type: Optional[str] = "unknown"
    short_desc: Optional[str] = None
    add_to_queue: QueueType = QueueType.ACTIVE
    priority: Priority = Priority.MEDIUM

class ManualEntityResponse(BaseModel):
    qid: str
    title: str
    type: str
    queue_type: QueueType
    message: str

# Queue schemas
class QueueEntryBase(BaseModel):
    qid: str
    queue_type: QueueType
    priority: Priority = Priority.MEDIUM
    notes: Optional[str] = None
    discovery_source: Optional[str] = None  # NEW

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
    operation: str  # move, delete, update_priority, update_status, approve_review, reject_review
    qids: List[str]
    target_queue: Optional[QueueType] = None
    priority: Optional[Priority] = None
    notes: Optional[str] = None

class BatchOperationResult(BaseModel):
    success_count: int
    error_count: int
    skipped_count: int = 0  # NEW - Smart deduplication skip count
    errors: List[Dict[str, str]]



# Add this to backend/utils/schemas.py if not already present:
class BulkReviewOperation(BaseModel):
    """Schema for bulk review operations (approve/reject specific QIDs)"""
    operation: str  # 'approve' or 'reject' 
    qids: List[str]  # List of specific QIDs to process
    target_queue: Optional[QueueType] = None  # Target queue (for approve operations)
    priority: Optional[Priority] = None  # Priority to assign
    notes: Optional[str] = None  # Optional notes

class BulkReviewResult(BaseModel):
    """Result of bulk review operations"""
    success_count: int
    error_count: int  
    skipped_count: int  # For deduplication skips
    errors: List[Dict[str, str]]  # List of QID-error pairs

    class Config:
        json_schema_extra = {
            "example": {
                "success_count": 5,
                "error_count": 1,
                "skipped_count": 2,
                "errors": [
                    {"qid": "Q123", "error": "Entity not found in review queue"},
                    {"qid": "Q456", "error": "Skipped: already_completed"}
                ]
            }
        }
# Extraction Schemas - NEW
class ExtractionConfig(BaseModel):
    max_depth: int = 3
    batch_size: int = 10
    max_workers: int = 5
    pause_between_requests: float = 1.0
    enable_deduplication: bool = True
    retry_attempts: int = 3
    auto_add_to_review: bool = True  # Auto-add discovered links to review queue

class ExtractionStartRequest(BaseModel):
    queue_types: List[QueueType] = [QueueType.ACTIVE]
    config: Optional[ExtractionConfig] = None
    session_name: Optional[str] = None

class ExtractionStatusResponse(BaseModel):
    status: ExtractionStatus
    session_id: Optional[int] = None
    current_entity: Optional[str] = None
    progress_percentage: float = 0
    total_entities: int = 0
    processed_entities: int = 0
    failed_entities: int = 0
    skipped_entities: int = 0
    discovered_entities: int = 0
    start_time: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

class ExtractionProgressUpdate(BaseModel):  # NEW - For WebSocket updates
    session_id: int
    current_entity_qid: str
    current_entity_title: str
    progress_percentage: float
    processed_count: int
    total_count: int
    discovered_links: int = 0
    skipped_duplicates: int = 0

class DiscoveredLinksUpdate(BaseModel):  # NEW - For WebSocket updates
    session_id: int
    parent_qid: str
    parent_title: str
    discovered_count: int
    added_to_review: int
    skipped_duplicates: int
    skipped_reasons: Dict[str, int]  # reason -> count

# Filter schemas
class EntityFilter(BaseModel):
    search: Optional[str] = None
    types: Optional[List[str]] = None
    status: Optional[List[EntityStatus]] = None
    queue_type: Optional[List[QueueType]] = None
    parent_qid: Optional[str] = None
    discovered_by: Optional[str] = None  # NEW
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
    total_in_review: int  # NEW
    queue_stats: List[QueueStats]
    type_stats: List[TypeStats]
    recent_activity: List[EntityResponse]
    active_extraction: Optional[ExtractionStatusResponse] = None  # NEW

class DeduplicationStats(BaseModel):  # NEW
    total_checked: int
    already_completed: int
    already_rejected: int
    already_in_queue: int
    total_skipped: int
    newly_added: int

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

class LinksDiscoveredMessage(WebSocketMessage):  # NEW
    type: str = "links_discovered"

class ExtractionStatusMessage(WebSocketMessage):  # NEW
    type: str = "extraction_status_changed"