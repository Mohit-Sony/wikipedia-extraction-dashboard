"""
Test script for universal Wikidata property extraction.

Tests the new extract_all_properties feature with real entities.
"""

import sys
import logging
from pathlib import Path

# Add Python_Helper to path
sys.path.insert(0, str(Path(__file__).parent / "Python_Helper"))

from wikidata_integration import WikidataIntegration, WikidataIntegrationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_entity(qid: str, title: str):
    """Test extraction for a specific entity"""
    print(f"\n{'='*80}")
    print(f"Testing: {title} ({qid})")
    print(f"{'='*80}\n")

    # Create Wikipedia data structure
    wikipedia_data = {
        'qid': qid,
        'title': title,
        'type': 'human'
    }

    # Initialize Wikidata integration with universal extraction
    config = WikidataIntegrationConfig(
        enable_enrichment=True,
        extract_all_properties=True  # UNIVERSAL EXTRACTION MODE
    )
    wikidata = WikidataIntegration(config=config)

    # Enrich the data
    enriched = wikidata.enrich(wikipedia_data, entity=None)

    # Display results
    print(f"Extraction Status: {enriched.get('structured_key_data_extracted')}")

    if enriched.get('structured_key_data_extracted'):
        structured_data = enriched.get('structured_key_data', {})
        print(f"\n✓ Successfully extracted {len(structured_data)} properties")
        print(f"\nProperties extracted:")
        for prop_id, prop_data in sorted(structured_data.items()):
            label = prop_data.get('label', prop_id)
            value = prop_data.get('value')
            value_type = prop_data.get('value_type')

            # Format value for display
            if isinstance(value, dict):
                if 'name' in value:
                    value_str = value['name']
                elif 'value' in value:
                    value_str = str(value['value'])
                else:
                    value_str = str(value)[:100]
            elif isinstance(value, list):
                value_str = f"[{len(value)} items]"
            else:
                value_str = str(value)[:100]

            print(f"  • {prop_id} ({label}): {value_str} [{value_type}]")

        # Display metadata
        if 'extraction_metadata' in enriched:
            metadata = enriched['extraction_metadata']
            print(f"\nExtraction Metadata:")
            print(f"  • Fetch Time: {metadata.get('wikidata_fetch_time', 'N/A')}s")
            print(f"  • Properties Extracted: {metadata.get('wikidata_properties_extracted', 0)}")
            print(f"  • Entity Type: {metadata.get('entity_type_standardized', 'N/A')}")
    else:
        print(f"\n✗ Failed to extract structured data")

    # Get statistics
    stats = wikidata.get_statistics()
    print(f"\nEnrichment Statistics:")
    print(f"  • Total Entities: {stats.get('total_enriched', 0)}")
    print(f"  • Successful: {stats.get('successful', 0)}")
    print(f"  • Failed: {stats.get('failed', 0)}")
    print(f"  • Success Rate: {stats.get('success_rate', 0)}%")

    return enriched


def main():
    """Run tests on multiple entities"""
    print("=" * 80)
    print("UNIVERSAL WIKIDATA PROPERTY EXTRACTION TEST")
    print("=" * 80)

    # Test entities
    test_cases = [
        ("Q111649067", "Prithviraj Sisodia"),  # Minimal properties (was failing before)
        ("Q2590601", "Rana Sanga"),  # Rich entity with ~31 properties
    ]

    results = []
    for qid, title in test_cases:
        try:
            result = test_entity(qid, title)
            results.append((qid, title, result))
        except Exception as e:
            logger.error(f"Error testing {qid}: {e}", exc_info=True)

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    for qid, title, result in results:
        extracted = result.get('structured_key_data_extracted', False)
        count = len(result.get('structured_key_data', {}))
        status = "✓ SUCCESS" if extracted else "✗ FAILED"
        print(f"{status}: {title} ({qid}) - {count} properties extracted")


if __name__ == "__main__":
    main()
