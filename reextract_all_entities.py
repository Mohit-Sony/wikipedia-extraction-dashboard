"""
Re-extract all entities with universal Wikidata property extraction.

Reads existing entity files from wikipedia_data, enriches them with ALL Wikidata properties,
and saves the updated versions to tmp/reextracted_data.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import time

# Add Python_Helper to path
sys.path.insert(0, str(Path(__file__).parent / "Python_Helper"))

from wikidata_integration import WikidataIntegration, WikidataIntegrationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tmp/reextraction.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def find_all_entity_files(base_dir: Path):
    """Find all JSON entity files in the wikipedia_data directory"""
    entity_files = list(base_dir.glob("**/*.json"))
    logger.info(f"Found {len(entity_files)} entity files")
    return entity_files


def load_entity_file(file_path: Path):
    """Load entity data from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return None


def save_entity_file(entity_data: dict, output_dir: Path, entity_type: str, qid: str):
    """Save enriched entity data to tmp folder"""
    try:
        # Create type subdirectory
        type_dir = output_dir / entity_type if entity_type else output_dir / "unknown"
        type_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        output_file = type_dir / f"{qid}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(entity_data, f, indent=2, ensure_ascii=False)

        return output_file
    except Exception as e:
        logger.error(f"Error saving {qid}: {e}")
        return None


def reextract_entity(wikidata: WikidataIntegration, entity_data: dict, file_path: Path):
    """Re-extract Wikidata structured data for an entity"""
    try:
        qid = entity_data.get('qid')
        title = entity_data.get('title', 'Unknown')
        entity_type = entity_data.get('type', 'unknown')

        if not qid:
            logger.warning(f"No QID found in {file_path}")
            return None, None

        logger.info(f"Processing: {title} ({qid})")

        # Get old property count
        old_structured_data = entity_data.get('structured_key_data', {})
        old_count = len(old_structured_data)
        old_extracted = entity_data.get('structured_key_data_extracted', False)

        # Re-enrich with universal extraction
        enriched = wikidata.enrich(entity_data, entity=None)

        # Get new property count
        new_structured_data = enriched.get('structured_key_data', {})
        new_count = len(new_structured_data)
        new_extracted = enriched.get('structured_key_data_extracted', False)

        # Calculate improvement
        improvement = new_count - old_count

        result = {
            'qid': qid,
            'title': title,
            'type': entity_type,
            'old_count': old_count,
            'new_count': new_count,
            'improvement': improvement,
            'old_extracted': old_extracted,
            'new_extracted': new_extracted,
            'status': 'success' if new_extracted else 'failed'
        }

        logger.info(
            f"  ✓ {title}: {old_count} → {new_count} properties "
            f"({'+' + str(improvement) if improvement >= 0 else str(improvement)})"
        )

        return enriched, result

    except Exception as e:
        logger.error(f"Error re-extracting {file_path}: {e}", exc_info=True)
        return None, {
            'qid': entity_data.get('qid', 'unknown'),
            'title': entity_data.get('title', 'Unknown'),
            'type': entity_data.get('type', 'unknown'),
            'status': 'error',
            'error': str(e)
        }


def main():
    """Main re-extraction process"""
    print("=" * 80)
    print("UNIVERSAL WIKIDATA PROPERTY RE-EXTRACTION")
    print("=" * 80)
    print()

    # Setup paths
    base_dir = Path("/Users/mohitsoni/work/The Indian History/ai pipieline/"
                   "Wikiextraction v2/Extraction dashboard/wikipedia-dashboard")
    source_dir = base_dir / "wikipedia_data"
    output_dir = base_dir / "tmp" / "reextracted_data"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")

    # Initialize Wikidata integration with universal extraction
    logger.info("Initializing Wikidata integration with universal extraction...")
    config = WikidataIntegrationConfig(
        enable_enrichment=True,
        extract_all_properties=True  # UNIVERSAL EXTRACTION MODE
    )
    wikidata = WikidataIntegration(config=config)
    logger.info("✓ Wikidata integration initialized")
    print()

    # Find all entity files
    print(f"Scanning: {source_dir}")
    entity_files = find_all_entity_files(source_dir)
    print(f"Found: {len(entity_files)} entities to re-extract")
    print()

    if not entity_files:
        logger.warning("No entity files found!")
        return

    # Process each entity
    results = []
    success_count = 0
    failed_count = 0
    error_count = 0

    start_time = time.time()

    print("Starting re-extraction...")
    print("-" * 80)

    for i, file_path in enumerate(entity_files, 1):
        print(f"\n[{i}/{len(entity_files)}] Processing: {file_path.name}")

        # Load entity
        entity_data = load_entity_file(file_path)
        if not entity_data:
            error_count += 1
            continue

        # Re-extract
        enriched, result = reextract_entity(wikidata, entity_data, file_path)

        if result is None:
            error_count += 1
            continue

        results.append(result)

        if result['status'] == 'success':
            success_count += 1
            # Save to tmp folder
            entity_type = result.get('type', 'unknown')
            qid = result.get('qid', 'unknown')
            output_file = save_entity_file(enriched, output_dir, entity_type, qid)
            if output_file:
                logger.info(f"  → Saved to: {output_file.relative_to(base_dir)}")
        elif result['status'] == 'failed':
            failed_count += 1
        else:
            error_count += 1

        # Small delay to avoid rate limiting
        time.sleep(0.5)

    elapsed_time = time.time() - start_time

    # Generate summary
    print()
    print("=" * 80)
    print("RE-EXTRACTION COMPLETE")
    print("=" * 80)
    print()

    print(f"Total Entities: {len(entity_files)}")
    print(f"✓ Successful: {success_count}")
    print(f"✗ Failed: {failed_count}")
    print(f"⚠ Errors: {error_count}")
    print(f"⏱ Time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
    print()

    # Property improvement statistics
    successful_results = [r for r in results if r['status'] == 'success']
    if successful_results:
        total_old = sum(r['old_count'] for r in successful_results)
        total_new = sum(r['new_count'] for r in successful_results)
        total_improvement = total_new - total_old

        print("Property Extraction Statistics:")
        print(f"  Before: {total_old} total properties")
        print(f"  After: {total_new} total properties")
        print(f"  Improvement: +{total_improvement} properties ({(total_improvement/total_old*100 if total_old > 0 else 0):.1f}%)")
        print()

    # Detailed results
    print("Detailed Results:")
    print("-" * 80)
    for result in results:
        status_icon = "✓" if result['status'] == 'success' else "✗"
        qid = result.get('qid', 'unknown')
        title = result.get('title', 'Unknown')
        old = result.get('old_count', 0)
        new = result.get('new_count', 0)
        improvement = result.get('improvement', 0)

        print(f"{status_icon} {qid} - {title}")
        print(f"   {old} → {new} properties ({'+' + str(improvement) if improvement >= 0 else str(improvement)})")

    print()
    print(f"Output saved to: {output_dir}")
    print()

    # Save summary to JSON
    summary_file = output_dir / "_reextraction_summary.json"
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_entities': len(entity_files),
        'successful': success_count,
        'failed': failed_count,
        'errors': error_count,
        'elapsed_time_seconds': elapsed_time,
        'results': results
    }

    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    logger.info(f"Summary saved to: {summary_file}")

    # Get enrichment statistics
    stats = wikidata.get_statistics()
    print("Wikidata Enrichment Statistics:")
    print(f"  Total Enriched: {stats.get('total_enriched', 0)}")
    print(f"  Success Rate: {stats.get('success_rate', 0)}%")
    print(f"  API Calls: {stats.get('api_calls', 0)}")
    print(f"  Cache Hits: {stats.get('cache_hits', 0)}")
    print(f"  Cache Hit Rate: {stats.get('cache_hit_rate', 0)}%")
    print()


if __name__ == "__main__":
    main()
