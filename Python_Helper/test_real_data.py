"""
Test Wikidata Integration on Real Extracted Wikipedia Data

Tests enrichment on actual Wikipedia JSON files from the wikipedia_data directory.
"""

import sys
import json
import logging
from pathlib import Path
from dataclasses import dataclass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import Wikidata integration
from wikidata_integration import WikidataIntegration, WikidataIntegrationConfig


@dataclass
class WikiEntity:
    """WikiEntity class for testing"""
    title: str
    qid: str
    type: str


def load_wikipedia_json(file_path: Path) -> dict:
    """Load Wikipedia JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return None


def test_entity_enrichment(wikidata: WikidataIntegration, json_file: Path, output_dir: Path):
    """Test enrichment on a single entity"""

    logger.info("=" * 80)
    logger.info(f"Processing: {json_file.name}")
    logger.info("=" * 80)

    # Load Wikipedia data
    wikipedia_data = load_wikipedia_json(json_file)
    if not wikipedia_data:
        return False

    title = wikipedia_data.get('title', 'Unknown')
    qid = json_file.stem  # Filename is the QID
    entity_type = json_file.parent.name  # Directory name is the type

    logger.info(f"Title: {title}")
    logger.info(f"QID: {qid}")
    logger.info(f"Type: {entity_type}")

    # Create WikiEntity
    entity = WikiEntity(title=title, qid=qid, type=entity_type)

    # Enrich with Wikidata
    logger.info("\nEnriching with Wikidata...")
    enriched_data = wikidata.enrich(wikipedia_data, entity)

    # Check results
    if enriched_data.get('structured_key_data_extracted'):
        structured_data = enriched_data.get('structured_key_data', {})
        metadata = enriched_data.get('extraction_metadata', {})

        logger.info(f"✓ SUCCESS!")
        logger.info(f"  Properties extracted: {len(structured_data)}")
        logger.info(f"  Entity type (standardized): {metadata.get('entity_type_standardized')}")
        logger.info(f"  Fetch time: {metadata.get('wikidata_fetch_time')}s")

        # Show extracted properties
        if structured_data:
            logger.info(f"\n  Extracted Properties:")
            for prop_id, prop_data in list(structured_data.items())[:10]:
                label = prop_data.get('label', 'unknown')
                value_type = prop_data.get('value_type', 'unknown')
                logger.info(f"    {prop_id:6} - {label:25} ({value_type})")

        # Save enriched data
        output_file = output_dir / f"{qid}_enriched.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)
        logger.info(f"\n  ✓ Saved to: {output_file}")

        return True
    else:
        logger.warning("✗ FAILED - No structured data extracted")
        return False


def main():
    """Main test function"""

    # Setup paths
    base_path = Path(__file__).parent.parent
    data_dir = base_path / "wikipedia_data"
    output_dir = base_path / "tmp" / "wikidata_enriched"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("WIKIDATA INTEGRATION TEST - REAL DATA")
    logger.info("=" * 80)
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Output directory: {output_dir}")

    # Initialize Wikidata integration
    logger.info("\nInitializing Wikidata Integration...")
    wikidata_config = WikidataIntegrationConfig(
        enable_enrichment=True,
        config_dir=str(base_path / "config" / "properties"),
        cache_file=str(base_path / "pipeline_state" / "entity_cache.pkl"),
        cache_ttl=3600,
        cache_maxsize=1000
    )
    wikidata = WikidataIntegration(config=wikidata_config, base_path=base_path)
    logger.info("✓ Initialized\n")

    # Find all JSON files in wikipedia_data
    json_files = []
    for entity_type_dir in data_dir.iterdir():
        if entity_type_dir.is_dir() and not entity_type_dir.name.startswith('.'):
            json_files.extend(entity_type_dir.glob("*.json"))

    logger.info(f"Found {len(json_files)} JSON files to process\n")

    # Test on each file
    results = {
        'total': len(json_files),
        'success': 0,
        'failed': 0
    }

    for idx, json_file in enumerate(json_files, 1):
        logger.info(f"\n[{idx}/{len(json_files)}]")
        success = test_entity_enrichment(wikidata, json_file, output_dir)

        if success:
            results['success'] += 1
        else:
            results['failed'] += 1

    # Final statistics
    logger.info("\n" + "=" * 80)
    logger.info("FINAL RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total files processed: {results['total']}")
    logger.info(f"Successful enrichments: {results['success']}")
    logger.info(f"Failed enrichments: {results['failed']}")
    logger.info(f"Success rate: {results['success']/results['total']*100:.1f}%")

    # Wikidata statistics
    logger.info("\n" + "=" * 80)
    logger.info("WIKIDATA STATISTICS")
    logger.info("=" * 80)
    wikidata.log_statistics()

    # Client metrics
    if hasattr(wikidata, 'wikidata_client'):
        logger.info("\n" + "=" * 80)
        logger.info("CLIENT PERFORMANCE METRICS")
        logger.info("=" * 80)
        wikidata.wikidata_client.log_metrics()

    logger.info("\n" + "=" * 80)
    logger.info(f"✓ All enriched files saved to: {output_dir}")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        sys.exit(1)
