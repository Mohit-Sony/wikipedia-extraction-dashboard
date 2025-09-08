# backend/database/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    queue_entries = relationship("QueueEntry", back_populates="entity")
    user_decisions = relationship("UserDecision", back_populates="entity")

class QueueEntry(Base):
    __tablename__ = "queue_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    qid = Column(String, ForeignKey("entities.qid"), nullable=False)
    queue_type = Column(String, nullable=False, index=True)  # active, rejected, on_hold, completed, failed
    priority = Column(Integer, default=1)  # 1=high, 2=medium, 3=low
    position = Column(Integer, default=0)
    added_by = Column(String, default="system")
    added_date = Column(DateTime, default=datetime.utcnow)
    processed_date = Column(DateTime)
    notes = Column(Text)
    
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
    config_snapshot = Column(Text)  # JSON string of pipeline config
    status = Column(String, default="active")  # active, completed, paused, failed
    
    # Relationships
    user_decisions = relationship("UserDecision", back_populates="session")

class UserDecision(Base):
    __tablename__ = "user_decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    qid = Column(String, ForeignKey("entities.qid"), nullable=False)
    session_id = Column(Integer, ForeignKey("extraction_sessions.id"))
    decision_type = Column(String, nullable=False)  # queue_add, queue_remove, priority_change, reject, approve
    decision_value = Column(String)  # queue name, priority level, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    reasoning = Column(Text)
    
    # Relationships
    entity = relationship("Entity", back_populates="user_decisions")
    session = relationship("ExtractionSession", back_populates="user_decisions")

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, default="default")
    preference_type = Column(String, nullable=False)  # filter_template, auto_rule, ui_setting
    preference_name = Column(String, nullable=False)
    preference_value = Column(Text, nullable=False)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)