# backend/database/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Entity(Base):
    __tablename__ = "entities"
    
    id = Column(Integer, primary_key=True, index=True)
    qid = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    type = Column(String, nullable=False, index=True)
    short_desc = Column(Text)
    num_links = Column(Integer, default=0)
    num_tables = Column(Integer, default=0)
    num_images = Column(Integer, default=0)
    num_chunks = Column(Integer, default=0)
    page_length = Column(Integer, default=0)
    extraction_date = Column(DateTime)
    last_modified = Column(DateTime)
    file_path = Column(String, nullable=False)
    status = Column(String, default="unprocessed", index=True)  # unprocessed, queued, processing, completed, failed, rejected
    parent_qid = Column(String, index=True)
    depth = Column(Integer, default=0, index=True)
    discovered_by = Column(String, index=True)  # NEW - QID of entity that discovered this one
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    queue_entries = relationship("QueueEntry", back_populates="entity")
    user_decisions = relationship("UserDecision", back_populates="entity")

class QueueEntry(Base):
    __tablename__ = "queue_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    qid = Column(String, ForeignKey("entities.qid"), nullable=False)
    queue_type = Column(String, nullable=False, index=True)  # active, rejected, on_hold, completed, failed, review, processing
    priority = Column(Integer, default=1)  # 1=high, 2=medium, 3=low
    position = Column(Integer, default=0)
    added_by = Column(String, default="system")
    added_date = Column(DateTime, default=datetime.utcnow)
    processed_date = Column(DateTime)
    notes = Column(Text)
    discovery_source = Column(String, index=True)  # NEW - QID of parent entity that discovered this
    
    # Relationships
    entity = relationship("Entity", back_populates="queue_entries")

class ExtractionSession(Base):
    __tablename__ = "extraction_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_name = Column(String, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    total_extracted = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)
    total_duplicates = Column(Integer, default=0)
    total_skipped = Column(Integer, default=0)  # NEW - Smart deduplication count
    config_snapshot = Column(Text)  # JSON string of pipeline config
    status = Column(String, default="active")  # active, completed, paused, cancelled, failed
    current_entity_qid = Column(String)  # NEW - Currently processing entity
    progress_percentage = Column(Float, default=0)  # NEW - Current progress
    
    # Relationships
    user_decisions = relationship("UserDecision", back_populates="session")

class UserDecision(Base):
    __tablename__ = "user_decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    qid = Column(String, ForeignKey("entities.qid"), nullable=False)
    session_id = Column(Integer, ForeignKey("extraction_sessions.id"))
    decision_type = Column(String, nullable=False)  # queue_add, queue_remove, priority_change, reject, approve, skip_duplicate
    decision_value = Column(String)  # queue name, priority level, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    reasoning = Column(Text)
    auto_decision = Column(Boolean, default=False)  # NEW - True if decision made by smart deduplication
    
    # Relationships
    entity = relationship("Entity", back_populates="user_decisions")
    session = relationship("ExtractionSession", back_populates="user_decisions")

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, default="default")
    preference_type = Column(String, nullable=False)  # filter_template, auto_rule, ui_setting, extraction_config
    preference_name = Column(String, nullable=False)
    preference_value = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExtractionLog(Base):
    __tablename__ = "extraction_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("extraction_sessions.id"))
    qid = Column(String, nullable=False)
    event_type = Column(String, nullable=False)  # started, completed, failed, skipped, discovered_links
    event_data = Column(JSON)  # Additional event data
    timestamp = Column(DateTime, default=datetime.utcnow)
    message = Column(Text)

    # Relationships
    session = relationship("ExtractionSession")

class TypeMapping(Base):
    __tablename__ = "type_mappings"

    id = Column(Integer, primary_key=True, index=True)
    wikidata_type = Column(String, unique=True, nullable=False, index=True)  # Wikidata P31 value or Wikipedia type
    wikidata_qid = Column(String, index=True)  # Optional: QID of the type itself
    mapped_type = Column(String, nullable=False, index=True)  # One of: person, location, event, dynasty, political_entity, timeline
    is_approved = Column(Boolean, default=False)  # Whether this mapping is approved
    confidence = Column(Float, default=1.0)  # Confidence score for auto-mapped types
    source = Column(String, default="manual")  # manual, auto, wikidata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, default="system")
    notes = Column(Text)  # Additional notes about this mapping