"""
Example: Wikidata Integration with Wikipedia Extraction Pipeline

This script demonstrates how to integrate Wikidata enrichment into
the existing Wikipedia extraction workflow.

Usage:
    python example_wikidata_integration.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from dataclasses import dataclass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import Wikipedia extractor
from wiki_extract import OptimizedWikipediaExtractor, ExtractionConfig, setup_logging

# Import Wikidata integration
from wikidata_integration import WikidataIntegration, WikidataIntegrationConfig


@dataclass
class WikiEntity:
    """Simple WikiEntity class for demonstration"""
    title: str
    qid: str
    type: str


async def extract_and_enrich_page(page_title: str):
    """
    Extract Wikipedia page and enrich with Wikidata.

    Args:
        page_title: Wikipedia page title to extract
    """
    # Setup logging
    logger = setup_logging(log_level="INFO", log_file="extraction.log")
    logger.info(f"Starting extraction and enrichment for: {page_title}")

    # Initialize Wikipedia extractor
    extraction_config = ExtractionConfig(
        max_concurrent_requests=10,
        enable_caching=True
    )
    extractor = OptimizedWikipediaExtractor(
        config=extraction_config,
        cache_dir="./cache"
    )

    # Initialize Wikidata integration
    wikidata_config = WikidataIntegrationConfig(
        enable_enrichment=True,
        config_dir="config/properties",
        cache_file="pipeline_state/entity_cache.pkl"
    )
    wikidata = WikidataIntegration(config=wikidata_config)

    try:
        # Step 1: Extract Wikipedia data
        logger.info("=" * 60)
        logger.info("STEP 1: Extracting Wikipedia data...")
        logger.info("=" * 60)

        wikipedia_data = await extractor.extract_page_data(page_title)

        logger.info(f"Wikipedia extraction complete:")
        logger.info(f"  - Title: {wikipedia_data.get('title')}")
        logger.info(f"  - QID: {wikipedia_data.get('qid', 'Not found')}")
        logger.info(f"  - Type: {wikipedia_data.get('type', 'Unknown')}")

        # Step 2: Enrich with Wikidata
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 2: Enriching with Wikidata structured data...")
        logger.info("=" * 60)

        # Create WikiEntity object
        entity = WikiEntity(
            title=wikipedia_data.get('title'),
            qid=wikipedia_data.get('qid'),
            type=wikipedia_data.get('type')
        )

        # Enrich with Wikidata
        enriched_data = wikidata.enrich(wikipedia_data, entity)

        # Check enrichment status
        if enriched_data.get('structured_key_data_extracted'):
            logger.info(f"Wikidata enrichment successful!")
            logger.info(f"  - Properties extracted: {len(enriched_data.get('structured_key_data', {}))}")
            logger.info(f"  - Entity type (standardized): {enriched_data.get('extraction_metadata', {}).get('entity_type_standardized')}")
            logger.info(f"  - Fetch time: {enriched_data.get('extraction_metadata', {}).get('wikidata_fetch_time')}s")

            # Show sample properties
            structured_data = enriched_data.get('structured_key_data', {})
            if structured_data:
                logger.info(f"\nSample properties:")
                for prop_id, prop_data in list(structured_data.items())[:5]:
                    logger.info(f"  - {prop_id} ({prop_data.get('label')}): {prop_data.get('value_type')}")

        else:
            logger.warning("Wikidata enrichment failed or not available")

        # Step 3: Display statistics
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 3: Statistics")
        logger.info("=" * 60)
        wikidata.log_statistics()

        # Step 4: Save cache
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 4: Saving cache")
        logger.info("=" * 60)
        wikidata.save_cache()

        return enriched_data

    except Exception as e:
        logger.error(f"Error during extraction/enrichment: {e}", exc_info=True)
        return None


async def main():
    """Main execution function"""
    # Test with Mahatma Gandhi
    test_pages = [
        "Mahatma Gandhi",
        # Add more test pages here
    ]

    for page_title in test_pages:
        print(f"\n{'=' * 80}")
        print(f"Processing: {page_title}")
        print(f"{'=' * 80}\n")

        enriched_data = await extract_and_enrich_page(page_title)

        if enriched_data:
            print(f"\n✓ Successfully processed: {page_title}")
        else:
            print(f"\n✗ Failed to process: {page_title}")


if __name__ == "__main__":
    asyncio.run(main())
