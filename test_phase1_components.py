#!/usr/bin/env python3
"""
Phase 1 Component Verification Script

Quick test to verify that all Phase 1 components can be imported
and initialized without errors.

Run this script to verify Phase 1 completion.
"""

import sys
from pathlib import Path

# Add Python_Helper to path
sys.path.insert(0, str(Path(__file__).parent / 'Python_Helper'))

def test_imports():
    """Test that all components can be imported."""
    print("Testing imports...")

    try:
        from wikidata import (
            PropertyConfigManager,
            WikidataClient,
            EntityReferenceCache,
            WikidataParser,
            WikidataEnricher
        )
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_property_config_manager():
    """Test PropertyConfigManager initialization and basic operations."""
    print("\nTesting PropertyConfigManager...")

    try:
        from wikidata import PropertyConfigManager

        # Initialize
        manager = PropertyConfigManager()
        print(f"  ✅ Initialized with {len(manager.configs)} configurations")

        # Get properties for person
        person_props = manager.get_properties_for_type('person')
        print(f"  ✅ Person entity has {len(person_props)} properties")

        # Test normalization
        normalized = manager._normalize_entity_type('human')
        assert normalized == 'person', "Entity type normalization failed"
        print(f"  ✅ Entity type normalization works ('human' → '{normalized}')")

        # Get all entity types
        entity_types = manager.get_all_entity_types()
        print(f"  ✅ Configured entity types: {', '.join(entity_types)}")

        return True
    except Exception as e:
        print(f"  ❌ PropertyConfigManager test failed: {e}")
        return False


def test_wikidata_client():
    """Test WikidataClient initialization."""
    print("\nTesting WikidataClient...")

    try:
        from wikidata import WikidataClient

        # Initialize
        client = WikidataClient(timeout=5, max_retries=2)
        print("  ✅ WikidataClient initialized")

        # Test context manager
        with WikidataClient() as test_client:
            print("  ✅ Context manager works")

        client.close()
        print("  ✅ Client cleanup successful")

        return True
    except Exception as e:
        print(f"  ❌ WikidataClient test failed: {e}")
        return False


def test_entity_reference_cache():
    """Test EntityReferenceCache initialization and basic operations."""
    print("\nTesting EntityReferenceCache...")

    try:
        from wikidata import EntityReferenceCache

        # Initialize (no disk persistence for test)
        cache = EntityReferenceCache()
        print("  ✅ EntityReferenceCache initialized")

        # Test put/get
        test_entity = {
            'qid': 'Q1001',
            'name': 'Test Entity',
            'description': 'Test description',
            'type': 'person'
        }
        cache.put('Q1001', test_entity)
        print("  ✅ Put operation successful")

        retrieved = cache.get('Q1001')
        assert retrieved is not None, "Failed to retrieve cached entity"
        assert retrieved['name'] == 'Test Entity', "Retrieved data doesn't match"
        print("  ✅ Get operation successful")

        # Test statistics
        stats = cache.get_statistics()
        print(f"  ✅ Cache statistics: {stats['hits']} hits, {stats['misses']} misses, hit rate: {stats['hit_rate']:.2%}")

        # Test contains
        assert 'Q1001' in cache, "Contains check failed"
        print("  ✅ Contains operation successful")

        return True
    except Exception as e:
        print(f"  ❌ EntityReferenceCache test failed: {e}")
        return False


def test_yaml_configs():
    """Test that all YAML configuration files are valid."""
    print("\nTesting YAML configuration files...")

    try:
        import yaml
        from pathlib import Path

        config_dir = Path('config/properties')
        expected_files = [
            'person.yaml',
            'event.yaml',
            'location.yaml',
            'dynasty.yaml',
            'political_entity.yaml',
            'other.yaml'
        ]

        for filename in expected_files:
            filepath = config_dir / filename
            if not filepath.exists():
                print(f"  ❌ Missing config file: {filename}")
                return False

            with open(filepath) as f:
                config = yaml.safe_load(f)

            entity_type = config.get('entity_type')
            properties = config.get('properties', [])

            print(f"  ✅ {filename}: {entity_type} with {len(properties)} properties")

        return True
    except Exception as e:
        print(f"  ❌ YAML config test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Phase 1 Component Verification")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("YAML Configs", test_yaml_configs()))
    results.append(("PropertyConfigManager", test_property_config_manager()))
    results.append(("WikidataClient", test_wikidata_client()))
    results.append(("EntityReferenceCache", test_entity_reference_cache()))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 Phase 1 verification SUCCESSFUL! All components working.")
        return 0
    else:
        print(f"\n⚠️  Phase 1 verification INCOMPLETE: {total - passed} test(s) failed.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
