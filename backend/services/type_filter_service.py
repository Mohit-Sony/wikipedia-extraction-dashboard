# backend/services/type_filter_service.py
import logging
from typing import List, Dict, Set
from sqlalchemy.orm import Session
from database.models import Entity, QueueEntry, TypeMapping
from utils.schemas import QueueType

logger = logging.getLogger(__name__)

class TypeFilterService:
    """Service for filtering entities by type for bulk operations"""

    # Default approved types for Indian history
    APPROVED_TYPES = {
        "person",
        "location",
        "event",
        "dynasty",
        "political_entity",
        "timeline"
    }

    def __init__(self, db: Session):
        self.db = db

    def get_type_mapping(self, wikidata_type: str) -> str:
        """
        Get mapped type for a wikidata type

        Args:
            wikidata_type: The type from wikidata/wikipedia

        Returns:
            Mapped standard type or the original type if no mapping exists
        """
        mapping = self.db.query(TypeMapping).filter(
            TypeMapping.wikidata_type == wikidata_type.lower(),
            TypeMapping.is_approved == True
        ).first()

        if mapping:
            return mapping.mapped_type

        # Check if type directly matches approved types
        if wikidata_type.lower() in self.APPROVED_TYPES:
            return wikidata_type.lower()

        return "other"

    def is_approved_type(self, entity_type: str) -> bool:
        """
        Check if entity type is in approved list

        Args:
            entity_type: Entity type to check

        Returns:
            True if approved, False otherwise
        """
        # Get mapped type first
        mapped_type = self.get_type_mapping(entity_type)
        return mapped_type in self.APPROVED_TYPES

    def filter_entities_by_approved_types(
        self,
        qids: List[str]
    ) -> Dict[str, List[str]]:
        """
        Filter entities by whether their type is approved

        Args:
            qids: List of entity QIDs to filter

        Returns:
            Dictionary with 'approved' and 'rejected' lists of QIDs
        """
        approved_qids = []
        rejected_qids = []
        unmapped_types = set()

        for qid in qids:
            entity = self.db.query(Entity).filter(Entity.qid == qid).first()

            if not entity:
                logger.warning(f"Entity {qid} not found")
                rejected_qids.append(qid)
                continue

            if self.is_approved_type(entity.type):
                approved_qids.append(qid)
            else:
                rejected_qids.append(qid)
                unmapped_types.add(entity.type)

        # Log unmapped types for admin review
        if unmapped_types:
            logger.info(f"Found unmapped types: {unmapped_types}")

        return {
            "approved": approved_qids,
            "rejected": rejected_qids,
            "unmapped_types": list(unmapped_types)
        }

    def get_unmapped_types_in_review_queue(self) -> List[Dict]:
        """
        Get all unique unmapped types currently in review queue

        Returns:
            List of dictionaries with type info and count
        """
        # Get all entities in review queue
        review_entities = self.db.query(Entity).join(QueueEntry).filter(
            QueueEntry.queue_type == QueueType.REVIEW.value
        ).all()

        # Count unmapped types
        type_counts = {}
        for entity in review_entities:
            mapped_type = self.get_type_mapping(entity.type)
            if mapped_type == "other":
                # This is an unmapped type
                if entity.type not in type_counts:
                    type_counts[entity.type] = {
                        "type": entity.type,
                        "count": 0,
                        "example_qids": []
                    }
                type_counts[entity.type]["count"] += 1
                if len(type_counts[entity.type]["example_qids"]) < 3:
                    type_counts[entity.type]["example_qids"].append({
                        "qid": entity.qid,
                        "title": entity.title
                    })

        return list(type_counts.values())

    def create_type_mapping(
        self,
        wikidata_type: str,
        mapped_type: str,
        wikidata_qid: str = None,
        is_approved: bool = True,
        source: str = "manual",
        created_by: str = "admin",
        notes: str = None
    ) -> TypeMapping:
        """
        Create a new type mapping

        Args:
            wikidata_type: The original wikidata/wikipedia type
            mapped_type: The standard type to map to
            wikidata_qid: Optional QID of the type itself
            is_approved: Whether this mapping is approved
            source: Source of mapping (manual, auto, wikidata)
            created_by: User who created this mapping
            notes: Additional notes

        Returns:
            Created TypeMapping object
        """
        # Check if mapping already exists
        existing = self.db.query(TypeMapping).filter(
            TypeMapping.wikidata_type == wikidata_type.lower()
        ).first()

        if existing:
            # Update existing mapping
            existing.mapped_type = mapped_type
            existing.wikidata_qid = wikidata_qid
            existing.is_approved = is_approved
            existing.source = source
            existing.created_by = created_by
            existing.notes = notes
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"Updated type mapping: {wikidata_type} -> {mapped_type}")
            return existing

        # Create new mapping
        mapping = TypeMapping(
            wikidata_type=wikidata_type.lower(),
            wikidata_qid=wikidata_qid,
            mapped_type=mapped_type,
            is_approved=is_approved,
            source=source,
            created_by=created_by,
            notes=notes
        )

        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)

        logger.info(f"Created type mapping: {wikidata_type} -> {mapped_type}")
        return mapping

    def get_all_type_mappings(self, approved_only: bool = False) -> List[TypeMapping]:
        """
        Get all type mappings

        Args:
            approved_only: Only return approved mappings

        Returns:
            List of TypeMapping objects
        """
        query = self.db.query(TypeMapping)

        if approved_only:
            query = query.filter(TypeMapping.is_approved == True)

        return query.order_by(TypeMapping.mapped_type, TypeMapping.wikidata_type).all()

    def delete_type_mapping(self, mapping_id: int) -> bool:
        """
        Delete a type mapping

        Args:
            mapping_id: ID of mapping to delete

        Returns:
            True if deleted, False if not found
        """
        mapping = self.db.query(TypeMapping).filter(TypeMapping.id == mapping_id).first()

        if not mapping:
            return False

        self.db.delete(mapping)
        self.db.commit()

        logger.info(f"Deleted type mapping: {mapping.wikidata_type} -> {mapping.mapped_type}")
        return True
