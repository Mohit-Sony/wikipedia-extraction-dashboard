#!/usr/bin/env python3
"""
Migration script to add mapped_type field to all existing entity JSON files.

This script:
1. Scans all JSON files in the wikipedia_data directory
2. For each file, determines the entity type from directory name
3. Gets the mapped type using TypeFilterService
4. Adds "mapped_type" field to the JSON root
5. Writes the updated JSON back to the file

Usage:
    python add_mapped_type_to_json.py --dry-run  # Preview changes
    python add_mapped_type_to_json.py            # Execute migration
    python add_mapped_type_to_json.py --limit 10 # Test on first 10 files
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any
import logging

# Add parent directory to path to import from backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import SessionLocal
from services.type_filter_service import TypeFilterService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EntityJSONMigrator:
    """Migrates entity JSON files to include mapped_type field"""

    def __init__(self, data_dir: str, dry_run: bool = False):
        self.data_dir = Path(data_dir)
        self.dry_run = dry_run
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'updated': 0,
            'already_has_field': 0,
            'errors': 0,
            'skipped': 0
        }
        self.db = SessionLocal()
        self.type_service = TypeFilterService(self.db)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def get_entity_type_from_path(self, file_path: Path) -> str:
        """Extract entity type from directory name"""
        # Parent directory name is the entity type
        return file_path.parent.name.replace('_', ' ')

    def get_qid_from_filename(self, file_path: Path) -> str:
        """Extract QID from filename"""
        return file_path.stem  # filename without .json extension

    def process_json_file(self, file_path: Path) -> bool:
        """
        Process a single JSON file to add mapped_type field

        Returns:
            True if file was updated, False otherwise
        """
        try:
            # Read the JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if mapped_type already exists
            if 'mapped_type' in data:
                logger.debug(f"File {file_path.name} already has mapped_type field")
                self.stats['already_has_field'] += 1
                return False

            # Get entity type from directory
            entity_type = self.get_entity_type_from_path(file_path)
            qid = self.get_qid_from_filename(file_path)

            # Get mapped type
            mapped_type = self.type_service.get_type_mapping(entity_type)

            logger.info(f"Processing {qid}: type='{entity_type}' -> mapped_type='{mapped_type}'")

            if self.dry_run:
                logger.info(f"[DRY RUN] Would add mapped_type='{mapped_type}' to {file_path}")
                self.stats['updated'] += 1
                return True

            # Add mapped_type field at the beginning of the JSON
            # Create new dict with mapped_type first, then all other fields
            updated_data = {'mapped_type': mapped_type}
            updated_data.update(data)

            # Write back to file with proper formatting
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✓ Updated {file_path.name} with mapped_type='{mapped_type}'")
            self.stats['updated'] += 1
            return True

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")
            self.stats['errors'] += 1
            return False
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.stats['errors'] += 1
            return False

    def scan_and_process(self, limit: int = None):
        """Scan all JSON files in data directory and process them"""
        logger.info(f"Scanning directory: {self.data_dir}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")

        if not self.data_dir.exists():
            logger.error(f"Data directory not found: {self.data_dir}")
            return

        # Collect all JSON files
        json_files = []
        for type_dir in self.data_dir.iterdir():
            if not type_dir.is_dir():
                continue

            for json_file in type_dir.glob("*.json"):
                json_files.append(json_file)

        self.stats['total_files'] = len(json_files)
        logger.info(f"Found {self.stats['total_files']} JSON files")

        # Apply limit if specified
        if limit:
            json_files = json_files[:limit]
            logger.info(f"Processing first {limit} files (limit applied)")

        # Process each file
        for i, json_file in enumerate(json_files, 1):
            logger.info(f"\n[{i}/{len(json_files)}] Processing {json_file.name}")
            self.process_json_file(json_file)
            self.stats['processed'] += 1

            # Progress update every 50 files
            if i % 50 == 0:
                self.print_progress()

    def print_progress(self):
        """Print current progress statistics"""
        logger.info(f"\n--- Progress Update ---")
        logger.info(f"Processed: {self.stats['processed']}/{self.stats['total_files']}")
        logger.info(f"Updated: {self.stats['updated']}")
        logger.info(f"Already has field: {self.stats['already_has_field']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"----------------------\n")

    def print_summary(self):
        """Print final summary of migration"""
        logger.info("\n" + "=" * 60)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Mode: {'DRY RUN (no changes made)' if self.dry_run else 'EXECUTED'}")
        logger.info(f"Total files found: {self.stats['total_files']}")
        logger.info(f"Files processed: {self.stats['processed']}")
        logger.info(f"Files updated: {self.stats['updated']}")
        logger.info(f"Files already had field: {self.stats['already_has_field']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("=" * 60)

        if self.dry_run and self.stats['updated'] > 0:
            logger.info("\nℹ️  This was a DRY RUN. Run without --dry-run to apply changes.")


def main():
    parser = argparse.ArgumentParser(
        description='Add mapped_type field to all entity JSON files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of files to process (for testing)'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='../wikipedia_data',
        help='Path to wikipedia_data directory (default: ../wikipedia_data)'
    )

    args = parser.parse_args()

    # Determine data directory path
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / args.data_dir

    logger.info("=" * 60)
    logger.info("Entity JSON Migration: Add mapped_type field")
    logger.info("=" * 60)

    # Run migration
    with EntityJSONMigrator(data_dir, dry_run=args.dry_run) as migrator:
        migrator.scan_and_process(limit=args.limit)
        migrator.print_summary()

    logger.info("\n✓ Migration complete!")


if __name__ == '__main__':
    main()
