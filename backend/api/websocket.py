# backend/api/websocket.py - UPDATED with extraction events
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from database.database import get_db
from utils.schemas import (
    WebSocketMessage, EntityProcessedMessage, QueueUpdatedMessage,
    ExtractionProgressUpdate, DiscoveredLinksUpdate
)
from typing import List, Dict, Any
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, client_info: Dict[str, Any] = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = client_info or {}
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_info:
            del self.connection_info[websocket]
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_to_filtered(self, message: Dict[str, Any], filter_func=None):
        """Broadcast message to connections matching filter criteria"""
        disconnected = []
        for connection in self.active_connections:
            try:
                # Apply filter if provided
                if filter_func and not filter_func(self.connection_info.get(connection, {})):
                    continue
                
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting filtered message: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    def get_connection_count(self) -> int:
        return len(self.active_connections)

# Global connection manager instance
manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial connection confirmation
        await manager.send_personal_message({
            "type": "connection_established",
            "data": {
                "timestamp": datetime.utcnow().isoformat(),
                "connection_count": manager.get_connection_count()
            }
        }, websocket)
        
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_client_message(message, websocket)
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }, websocket)
            except Exception as e:
                logger.error(f"Error handling client message: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "data": {"message": str(e)}
                }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def handle_client_message(message: Dict[str, Any], websocket: WebSocket):
    """Handle messages received from client"""
    message_type = message.get("type")
    data = message.get("data", {})
    
    if message_type == "subscribe":
        # Client wants to subscribe to specific updates
        topics = data.get("topics", [])
        manager.connection_info[websocket]["subscriptions"] = topics
        await manager.send_personal_message({
            "type": "subscription_confirmed",
            "data": {"topics": topics}
        }, websocket)
        
    elif message_type == "unsubscribe":
        # Client wants to unsubscribe from topics
        topics = data.get("topics", [])
        current_subs = manager.connection_info[websocket].get("subscriptions", [])
        updated_subs = [topic for topic in current_subs if topic not in topics]
        manager.connection_info[websocket]["subscriptions"] = updated_subs
        await manager.send_personal_message({
            "type": "unsubscription_confirmed",
            "data": {"topics": topics}
        }, websocket)
        
    elif message_type == "ping":
        # Health check
        await manager.send_personal_message({
            "type": "pong",
            "data": {"timestamp": datetime.utcnow().isoformat()}
        }, websocket)
        
    else:
        await manager.send_personal_message({
            "type": "error",
            "data": {"message": f"Unknown message type: {message_type}"}
        }, websocket)

# Functions to be called by other parts of the application

async def notify_entity_processed(qid: str, entity_data: Dict[str, Any]):
    """Notify all connected clients that an entity has been processed"""
    message = {
        "type": "entity_processed",
        "data": {
            "qid": qid,
            "title": entity_data.get("title", ""),
            "type": entity_data.get("type", ""),
            "status": entity_data.get("status", ""),
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "num_links": entity_data.get("num_links", 0),
                "num_tables": entity_data.get("num_tables", 0),
                "num_images": entity_data.get("num_images", 0),
                "page_length": entity_data.get("page_length", 0)
            }
        }
    }
    
    # Filter to clients subscribed to entity updates
    def should_send(conn_info):
        subs = conn_info.get("subscriptions", [])
        return "entities" in subs or "all" in subs
    
    await manager.broadcast_to_filtered(message, should_send)

async def notify_queue_updated(queue_type: str, change_data: Dict[str, Any]):
    """Notify all connected clients that a queue has been updated"""
    message = {
        "type": "queue_updated",
        "data": {
            "queue_type": queue_type,
            "change_type": change_data.get("change_type", "unknown"),  # added, removed, moved
            "qid": change_data.get("qid"),
            "count_change": change_data.get("count_change", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    # Filter to clients subscribed to queue updates
    def should_send(conn_info):
        subs = conn_info.get("subscriptions", [])
        return "queues" in subs or "all" in subs
    
    await manager.broadcast_to_filtered(message, should_send)

# NEW: Extraction-specific notification functions

async def notify_extraction_progress(progress_data: Dict[str, Any]):
    """Notify clients about extraction progress"""
    message = {
        "type": "extraction_progress",
        "data": {
            "session_id": progress_data.get("session_id"),
            "current_entity_qid": progress_data.get("current_entity_qid"),
            "current_entity_title": progress_data.get("current_entity_title"),
            "progress_percentage": progress_data.get("progress_percentage", 0),
            "processed_count": progress_data.get("processed_count", 0),
            "total_count": progress_data.get("total_count", 0),
            "discovered_links": progress_data.get("discovered_links", 0),
            "skipped_duplicates": progress_data.get("skipped_duplicates", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    # Filter to clients subscribed to extraction updates
    def should_send(conn_info):
        subs = conn_info.get("subscriptions", [])
        return "extraction" in subs or "progress" in subs or "all" in subs
    
    await manager.broadcast_to_filtered(message, should_send)

async def notify_links_discovered(discovery_data: Dict[str, Any]):
    """Notify clients about newly discovered links"""
    message = {
        "type": "links_discovered",
        "data": {
            "session_id": discovery_data.get("session_id"),
            "parent_qid": discovery_data.get("parent_qid"),
            "parent_title": discovery_data.get("parent_title"),
            "discovered_count": discovery_data.get("discovered_count", 0),
            "added_to_review": discovery_data.get("added_to_review", 0),
            "skipped_duplicates": discovery_data.get("skipped_duplicates", 0),
            "skipped_reasons": discovery_data.get("skipped_reasons", {}),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    # Filter to clients subscribed to discovery updates
    def should_send(conn_info):
        subs = conn_info.get("subscriptions", [])
        return "discovery" in subs or "extraction" in subs or "all" in subs
    
    await manager.broadcast_to_filtered(message, should_send)

async def notify_extraction_status_change(status_data: Dict[str, Any]):
    """Notify clients about extraction status changes"""
    message = {
        "type": "extraction_status_change",
        "data": {
            "status": status_data.get("status", ""),
            "session_id": status_data.get("session_id"),
            "session_name": status_data.get("session_name"),
            "message": status_data.get("message", ""),
            "config": status_data.get("config", {}),
            "total_extracted": status_data.get("total_extracted", 0),
            "total_errors": status_data.get("total_errors", 0),
            "total_skipped": status_data.get("total_skipped", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    # Broadcast to all connected clients
    await manager.broadcast(message)

async def notify_batch_operation_complete(operation_data: Dict[str, Any]):
    """Notify clients when batch operations complete"""
    message = {
        "type": "batch_operation_complete",
        "data": {
            "operation": operation_data.get("operation", ""),
            "success_count": operation_data.get("success_count", 0),
            "error_count": operation_data.get("error_count", 0),
            "skipped_count": operation_data.get("skipped_count", 0),  # NEW
            "total_processed": operation_data.get("total_processed", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    # Filter to clients subscribed to batch operation updates
    def should_send(conn_info):
        subs = conn_info.get("subscriptions", [])
        return "batch_operations" in subs or "all" in subs
    
    await manager.broadcast_to_filtered(message, should_send)

async def notify_deduplication_stats(dedup_data: Dict[str, Any]):
    """Notify clients about deduplication statistics"""
    message = {
        "type": "deduplication_stats",
        "data": {
            "session_id": dedup_data.get("session_id"),
            "parent_qid": dedup_data.get("parent_qid"),
            "total_checked": dedup_data.get("total_checked", 0),
            "already_completed": dedup_data.get("already_completed", 0),
            "already_rejected": dedup_data.get("already_rejected", 0),
            "already_in_queue": dedup_data.get("already_in_queue", 0),
            "total_skipped": dedup_data.get("total_skipped", 0),
            "newly_added": dedup_data.get("newly_added", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    # Filter to clients subscribed to deduplication updates
    def should_send(conn_info):
        subs = conn_info.get("subscriptions", [])
        return "deduplication" in subs or "extraction" in subs or "all" in subs
    
    await manager.broadcast_to_filtered(message, should_send)

async def notify_system_status_change(status_data: Dict[str, Any]):
    """Notify clients about system status changes"""
    message = {
        "type": "system_status_change",
        "data": {
            "status": status_data.get("status", ""),
            "message": status_data.get("message", ""),
            "details": status_data.get("details", {}),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    # Broadcast to all connected clients
    await manager.broadcast(message)

async def notify_error_occurred(error_data: Dict[str, Any]):
    """Notify clients about errors"""
    message = {
        "type": "error_occurred",
        "data": {
            "error_type": error_data.get("error_type", ""),
            "error_message": error_data.get("error_message", ""),
            "qid": error_data.get("qid"),
            "session_id": error_data.get("session_id"),
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    # Filter to clients subscribed to error updates
    def should_send(conn_info):
        subs = conn_info.get("subscriptions", [])
        return "errors" in subs or "all" in subs
    
    await manager.broadcast_to_filtered(message, should_send)

# Utility endpoints for WebSocket management

@router.get("/websocket/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return {
        "total_connections": manager.get_connection_count(),
        "connection_details": [
            {
                "subscriptions": info.get("subscriptions", []),
                "connected_at": info.get("connected_at", "unknown")
            }
            for info in manager.connection_info.values()
        ]
    }

@router.post("/websocket/broadcast")
async def broadcast_message(message: Dict[str, Any]):
    """Manually broadcast a message to all connected clients (for testing)"""
    await manager.broadcast(message)
    return {"message": "Broadcast sent", "connection_count": manager.get_connection_count()}