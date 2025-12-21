"""
Simple Wikidata Integration Test

Tests the Wikidata enrichment without the full Wikipedia extraction pipeline.
"""

import sys
import json
import logging
from pathlib import Path

# Setup simple logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import Wikidata integration
from wikidata_integration import WikidataIntegration, WikidataIntegrationConfig
from dataclasses import dataclass

@dataclass
class WikiEntity:
    """Simple WikiEntity class for testing"""
    title: str
    qid: str
    type: str


def test_wikidata_enrichment():
    """Test Wikidata enrichment with a known entity"""

    logger.info("=" * 70)
    logger.info("WIKIDATA INTEGRATION TEST")
    logger.info("=" * 70)

    # Initialize Wikidata integration
    logger.info("\n1. Initializing Wikidata Integration...")
    wikidata_config = WikidataIntegrationConfig(
        enable_enrichment=True,
        config_dir="../config/properties",
        cache_file="../pipeline_state/entity_cache.pkl",
        cache_ttl=3600,
        cache_maxsize=1000
    )
    wikidata = WikidataIntegration(config=wikidata_config)
    logger.info("✓ Wikidata integration initialized")

    # Create mock Wikipedia data (simulating what Wikipedia extraction would provide)
    logger.info("\n2. Creating mock Wikipedia data for Mahatma Gandhi (Q1001)...")
    wikipedia_data = {
        'title': 'Mahatma Gandhi',
        'qid': 'Q1001',
        'type': 'human',
        'content': {
            'extract': 'Mohandas Karamchand Gandhi was an Indian lawyer...',
            'summary': 'Indian independence activist'
        },
        'metadata': {
            'page_id': '19379'
        }
    }
    logger.info(f"✓ Mock data created: {wikipedia_data['title']} ({wikipedia_data['qid']})")

    # Create WikiEntity
    entity = WikiEntity(
        title=wikipedia_data['title'],
        qid=wikipedia_data['qid'],
        type=wikipedia_data['type']
    )

    # Enrich with Wikidata
    logger.info("\n3. Enriching with Wikidata...")
    logger.info("   (This will fetch data from Wikidata API...)")
    enriched_data = wikidata.enrich(wikipedia_data, entity)

    # Check results
    logger.info("\n4. Checking enrichment results...")
    if enriched_data.get('structured_key_data_extracted'):
        logger.info("✓ Wikidata enrichment SUCCESSFUL!")

        structured_data = enriched_data.get('structured_key_data', {})
        metadata = enriched_data.get('extraction_metadata', {})

        logger.info(f"\n   Properties extracted: {len(structured_data)}")
        logger.info(f"   Entity type (standardized): {metadata.get('entity_type_standardized')}")
        logger.info(f"   Fetch time: {metadata.get('wikidata_fetch_time')}s")

        # Display extracted properties
        logger.info("\n5. Extracted Properties:")
        logger.info("   " + "=" * 66)
        for prop_id, prop_data in structured_data.items():
            label = prop_data.get('label', 'unknown')
            value_type = prop_data.get('value_type', 'unknown')
            value = prop_data.get('value')

            # Format value for display
            if value_type == 'time':
                display_value = value.get('value', 'N/A')
            elif value_type == 'wikibase-item':
                display_value = f"{value.get('name', 'N/A')} ({value.get('qid', 'N/A')})"
            elif value_type == 'array':
                display_value = f"[{len(value)} items]"
            elif value_type == 'coordinate':
                display_value = f"({value.get('latitude')}, {value.get('longitude')})"
            else:
                display_value = str(value)[:50]

            logger.info(f"   {prop_id:6} | {label:25} | {value_type:15} | {display_value}")

        logger.info("   " + "=" * 66)

        # Display relationship metadata
        rel_metadata = metadata.get('relationship_metadata', {})
        if rel_metadata:
            logger.info("\n6. Relationship Metadata:")
            logger.info(f"   Family connections: {rel_metadata.get('family_connections', 0)}")
            logger.info(f"   Political connections: {rel_metadata.get('political_connections', 0)}")
            logger.info(f"   Geographic connections: {rel_metadata.get('geographic_connections', 0)}")
            logger.info(f"   Total unique entities: {rel_metadata.get('total_unique_entities_referenced', 0)}")

        # Display statistics
        logger.info("\n7. Performance Statistics:")
        wikidata.log_statistics()

        # Save sample output to file
        logger.info("\n8. Saving sample output...")
        output_file = Path(__file__).parent / "wikidata_test_output.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)
        logger.info(f"✓ Sample output saved to: {output_file}")

        # Display a sample of the structured_key_data
        logger.info("\n9. Sample Structured Data (P569 - date_of_birth):")
        if 'P569' in structured_data:
            logger.info(json.dumps(structured_data['P569'], indent=2))

        logger.info("\n" + "=" * 70)
        logger.info("TEST COMPLETED SUCCESSFULLY ✓")
        logger.info("=" * 70)

        return True
    else:
        logger.error("✗ Wikidata enrichment FAILED")
        logger.error(f"   structured_key_data_extracted: {enriched_data.get('structured_key_data_extracted')}")
        return False


if __name__ == "__main__":
    try:
        success = test_wikidata_enrichment()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        sys.exit(1)
