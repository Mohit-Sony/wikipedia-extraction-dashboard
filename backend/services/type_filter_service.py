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
        "timeline",
        "other"
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

    def get_unmapped_types_in_review_queue(
        self,
        limit: int = 60,
        offset: int = 0,
        sort_by: str = "count",
        sort_order: str = "desc"
    ) -> Dict:
        """
        Get all unique unmapped types currently in review queue with pagination

        Args:
            limit: Number of types to return
            offset: Offset for pagination
            sort_by: Field to sort by (count or type)
            sort_order: Sort order (asc or desc)

        Returns:
            Dictionary with types list and pagination info
        """
        # Get all entities in review queue
        review_entities = self.db.query(Entity).join(QueueEntry).filter(
            QueueEntry.queue_type == QueueType.REVIEW.value
        ).all()

        # Count unmapped types (types that don't have a mapping in database)
        type_counts = {}
        for entity in review_entities:
            # Check if there's an actual mapping in the database
            mapping = self.db.query(TypeMapping).filter(
                TypeMapping.wikidata_type == entity.type.lower(),
                TypeMapping.is_approved == True
            ).first()

            # Only include if NO mapping exists OR if type is not in APPROVED_TYPES
            has_no_mapping = mapping is None and entity.type.lower() not in self.APPROVED_TYPES

            if has_no_mapping:
                # This is truly an unmapped type
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

        # Convert to list and sort
        all_types = list(type_counts.values())

        # Sort by specified field
        reverse = sort_order.lower() == "desc"
        if sort_by == "count":
            all_types.sort(key=lambda x: x["count"], reverse=reverse)
        elif sort_by == "type":
            all_types.sort(key=lambda x: x["type"].lower(), reverse=reverse)

        # Apply pagination
        total = len(all_types)
        paginated_types = all_types[offset:offset + limit]

        return {
            "types": paginated_types,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }

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

    def bulk_create_type_mappings(
        self,
        mappings_data: List[Dict],
        fail_on_error: bool = False
    ) -> Dict:
        """
        Create multiple type mappings at once

        Args:
            mappings_data: List of dictionaries with mapping data
            fail_on_error: If True, rollback all on any error (atomic). If False, skip errors.

        Returns:
            Dictionary with success/error counts and details
        """
        results = {
            "success": [],
            "errors": [],
            "total": len(mappings_data),
            "success_count": 0,
            "error_count": 0
        }

        for idx, mapping_data in enumerate(mappings_data):
            try:
                # Validate required fields
                if not mapping_data.get("wikidata_type"):
                    raise ValueError("wikidata_type is required")
                if not mapping_data.get("mapped_type"):
                    raise ValueError("mapped_type is required")

                # Validate mapped_type
                if mapping_data["mapped_type"] not in self.APPROVED_TYPES:
                    raise ValueError(f"Invalid mapped_type. Must be one of: {', '.join(self.APPROVED_TYPES)}")

                # Create mapping
                mapping = self.create_type_mapping(
                    wikidata_type=mapping_data.get("wikidata_type"),
                    mapped_type=mapping_data.get("mapped_type"),
                    wikidata_qid=mapping_data.get("wikidata_qid"),
                    is_approved=mapping_data.get("is_approved", True),
                    source=mapping_data.get("source", "bulk_import"),
                    created_by=mapping_data.get("created_by", "admin"),
                    notes=mapping_data.get("notes")
                )

                results["success"].append({
                    "index": idx,
                    "wikidata_type": mapping_data.get("wikidata_type"),
                    "mapped_type": mapping_data.get("mapped_type"),
                    "id": mapping.id
                })
                results["success_count"] += 1

            except Exception as e:
                error_msg = str(e)
                results["errors"].append({
                    "index": idx,
                    "wikidata_type": mapping_data.get("wikidata_type", "unknown"),
                    "error": error_msg
                })
                results["error_count"] += 1

                if fail_on_error:
                    self.db.rollback()
                    logger.error(f"Bulk create failed at index {idx}: {error_msg}")
                    raise Exception(f"Bulk create failed at row {idx + 1}: {error_msg}")

        logger.info(f"Bulk create completed: {results['success_count']} success, {results['error_count']} errors")
        return results
