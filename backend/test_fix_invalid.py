#!/usr/bin/env python3
"""
Test script to identify invalid completed entities
Run this before calling the API endpoint to see what would be fixed
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import and_
from database.database import SessionLocal
from database.models import Entity, QueueEntry
from utils.schemas import QueueType, EntityStatus

def find_invalid_completed_entities():
    """Find entities marked as completed but with no data"""
    db = SessionLocal()

    try:
        # Find all invalid completed entities
        invalid_entities = db.query(Entity).join(
            QueueEntry, Entity.qid == QueueEntry.qid
        ).filter(
            and_(
                Entity.status == EntityStatus.COMPLETED.value,
                QueueEntry.queue_type == QueueType.COMPLETED.value,
                Entity.num_links == 0,
                Entity.num_tables == 0,
                Entity.num_images == 0,
                Entity.num_chunks == 0,
                Entity.page_length == 0
            )
        ).all()

        print(f"\n{'='*80}")
        print(f"INVALID COMPLETED ENTITIES REPORT")
        print(f"{'='*80}\n")

        if not invalid_entities:
            print("✅ No invalid completed entities found!")
            print("All completed entities have valid data.")
            return

        print(f"🚨 Found {len(invalid_entities)} entities marked as COMPLETED with NO DATA:\n")

        print(f"{'QID':<15} {'Title':<40} {'Type':<20}")
        print(f"{'-'*75}")

        for entity in invalid_entities[:20]:  # Show first 20
            title = entity.title[:37] + "..." if len(entity.title) > 40 else entity.title
            entity_type = entity.type[:17] + "..." if len(entity.type) > 20 else entity.type
            print(f"{entity.qid:<15} {title:<40} {entity_type:<20}")

        if len(invalid_entities) > 20:
            print(f"\n... and {len(invalid_entities) - 20} more")

        print(f"\n{'='*80}")
        print(f"SUMMARY")
        print(f"{'='*80}")
        print(f"Total invalid entities: {len(invalid_entities)}")
        print(f"\nThese entities will be:")
        print(f"  • Status changed: 'completed' → 'failed'")
        print(f"  • Queue moved: COMPLETED → FAILED")
        print(f"\nTo fix these entities, call the API endpoint:")
        print(f"  POST http://localhost:8000/api/entities/fix-invalid-completed")
        print(f"\nOr use dry-run mode first to preview:")
        print(f"  POST http://localhost:8000/api/entities/fix-invalid-completed?dry_run=true")
        print(f"{'='*80}\n")

    finally:
        db.close()

if __name__ == "__main__":
    find_invalid_completed_entities()
