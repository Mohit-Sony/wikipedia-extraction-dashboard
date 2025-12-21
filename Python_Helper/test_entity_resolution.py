"""
Test Entity Reference Resolution

Tests that entity references (like father, mother, spouse) are properly resolved
with names and descriptions from Wikidata.
"""

import sys
import json
import logging
from pathlib import Path

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
from dataclasses import dataclass

@dataclass
class WikiEntity:
    """WikiEntity class for testing"""
    title: str
    qid: str
    type: str


def main():
    """Test entity reference resolution"""

    logger.info("=" * 80)
    logger.info("TESTING ENTITY REFERENCE RESOLUTION")
    logger.info("=" * 80)

    # Initialize Wikidata integration
    base_path = Path(__file__).parent.parent
    wikidata_config = WikidataIntegrationConfig(
        enable_enrichment=True,
        config_dir=str(base_path / "config" / "properties"),
        cache_file=str(base_path / "pipeline_state" / "entity_cache.pkl"),
        cache_ttl=3600,
        cache_maxsize=1000
    )
    wikidata = WikidataIntegration(config=wikidata_config, base_path=base_path)
    logger.info("✓ Wikidata integration initialized\n")

    # Load Akbar data
    data_file = base_path / "wikipedia_data" / "human" / "Q8597.json"
    with open(data_file, 'r', encoding='utf-8') as f:
        wikipedia_data = json.load(f)

    logger.info(f"Testing with: Akbar (Q8597)")
    logger.info("=" * 80)

    # Create WikiEntity
    entity = WikiEntity(title="Akbar", qid="Q8597", type="human")

    # Enrich with Wikidata
    logger.info("\nEnriching with Wikidata (this will fetch entity references)...")
    enriched_data = wikidata.enrich(wikipedia_data, entity)

    if enriched_data.get('structured_key_data_extracted'):
        structured_data = enriched_data.get('structured_key_data', {})

        logger.info("\n" + "=" * 80)
        logger.info("CHECKING ENTITY REFERENCES")
        logger.info("=" * 80)

        # Check father (P22)
        if 'P22' in structured_data:
            father = structured_data['P22']['value']
            logger.info(f"\nFather (P22):")
            logger.info(f"  QID: {father.get('qid')}")
            logger.info(f"  Name: {father.get('name')}")
            logger.info(f"  Description: {father.get('description')}")
            logger.info(f"  Type: {father.get('type')}")

            if father.get('name') and father.get('name') != father.get('qid'):
                logger.info(f"  ✓ Name resolved successfully!")
            else:
                logger.warning(f"  ✗ Name not resolved (still showing QID)")

        # Check mother (P25)
        if 'P25' in structured_data:
            mother = structured_data['P25']['value']
            logger.info(f"\nMother (P25):")
            logger.info(f"  QID: {mother.get('qid')}")
            logger.info(f"  Name: {mother.get('name')}")
            logger.info(f"  Description: {mother.get('description')}")
            logger.info(f"  Type: {mother.get('type')}")

            if mother.get('name') and mother.get('name') != mother.get('qid'):
                logger.info(f"  ✓ Name resolved successfully!")
            else:
                logger.warning(f"  ✗ Name not resolved (still showing QID)")

        # Check children (P40)
        if 'P40' in structured_data:
            children = structured_data['P40']['value']
            logger.info(f"\nChildren (P40): {len(children)} children")
            for idx, child in enumerate(children[:3], 1):  # Show first 3
                logger.info(f"\n  Child {idx}:")
                logger.info(f"    QID: {child.get('qid')}")
                logger.info(f"    Name: {child.get('name')}")
                logger.info(f"    Description: {child.get('description')}")

                if child.get('name') and child.get('name') != child.get('qid'):
                    logger.info(f"    ✓ Name resolved!")
                else:
                    logger.warning(f"    ✗ Name not resolved")

        # Save sample
        output_file = base_path / "tmp" / "test_entity_resolution_output.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)

        logger.info(f"\n" + "=" * 80)
        logger.info(f"Full output saved to: {output_file}")
        logger.info("=" * 80)

        # Show client metrics
        logger.info("\n" + "=" * 80)
        logger.info("CLIENT METRICS")
        logger.info("=" * 80)
        wikidata.wikidata_client.log_metrics()

    else:
        logger.error("Enrichment failed!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
