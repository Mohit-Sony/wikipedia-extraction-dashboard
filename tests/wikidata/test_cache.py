"""Unit tests for EntityReferenceCache."""

import pytest
import tempfile
import pickle
from pathlib import Path
from wikidata.cache import EntityReferenceCache


class TestEntityReferenceCache:
    """Test suite for EntityReferenceCache."""

    def test_initialization_no_file(self):
        """Test cache initialization without persistence file."""
        cache = EntityReferenceCache()

        assert cache.cache == {}
        assert cache.cache_file is None
        assert cache.stats['hits'] == 0
        assert cache.stats['misses'] == 0

    def test_initialization_with_file(self):
        """Test cache initialization with persistence file."""
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            cache_file = f.name

        try:
            cache = EntityReferenceCache(cache_file=cache_file)
            assert str(cache.cache_file) == cache_file
        finally:
            Path(cache_file).unlink(missing_ok=True)

    def test_put_and_get(self):
        """Test basic put and get operations."""
        cache = EntityReferenceCache()

        entity_data = {
            "qid": "Q1001",
            "name": "Mahatma Gandhi",
            "description": "Indian independence leader",
            "type": "human"
        }

        cache.put("Q1001", entity_data)
        result = cache.get("Q1001")

        assert result == entity_data
        assert cache.stats['hits'] == 1
        assert cache.stats['misses'] == 0

    def test_get_miss(self):
        """Test cache miss."""
        cache = EntityReferenceCache()

        result = cache.get("Q999999")

        assert result is None
        assert cache.stats['misses'] == 1
        assert cache.stats['hits'] == 0

    def test_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        cache = EntityReferenceCache()

        # Add some data
        cache.put("Q1", {"name": "Entity 1"})
        cache.put("Q2", {"name": "Entity 2"})

        # 2 hits
        cache.get("Q1")
        cache.get("Q2")

        # 1 miss
        cache.get("Q999")

        hit_rate = cache.get_hit_rate()
        assert hit_rate == pytest.approx(2/3, 0.01)

    def test_hit_rate_no_queries(self):
        """Test hit rate when no queries have been made."""
        cache = EntityReferenceCache()
        hit_rate = cache.get_hit_rate()

        assert hit_rate == 0.0

    def test_persistence_save_load(self):
        """Test saving and loading cache from disk."""
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            cache_file = f.name

        try:
            # Create cache and add data
            cache1 = EntityReferenceCache(cache_file=cache_file)
            cache1.put("Q1001", {"name": "Gandhi"})
            cache1.put("Q1002", {"name": "Nehru"})
            cache1.save()

            # Load into new cache
            cache2 = EntityReferenceCache(cache_file=cache_file)

            assert cache2.get("Q1001")["name"] == "Gandhi"
            assert cache2.get("Q1002")["name"] == "Nehru"
        finally:
            Path(cache_file).unlink(missing_ok=True)

    def test_auto_save(self):
        """Test auto-save mechanism."""
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            cache_file = f.name

        try:
            cache = EntityReferenceCache(cache_file=cache_file, auto_save_interval=5)

            # Add 6 items (should trigger auto-save at 5)
            for i in range(6):
                cache.put(f"Q{i}", {"name": f"Entity {i}"})

            # File should exist and contain data
            assert Path(cache_file).exists()

            # Verify by loading
            cache2 = EntityReferenceCache(cache_file=cache_file)
            assert cache2.get("Q0") is not None
        finally:
            Path(cache_file).unlink(missing_ok=True)

    def test_thread_safety(self):
        """Test thread-safe operations."""
        import threading

        cache = EntityReferenceCache()

        def worker(thread_id):
            for i in range(10):
                qid = f"Q{thread_id}_{i}"
                cache.put(qid, {"name": f"Entity {qid}"})
                cache.get(qid)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should have 50 entities (5 threads * 10 entities)
        assert len(cache.cache) == 50

    def test_clear_cache(self):
        """Test clearing cache."""
        cache = EntityReferenceCache()

        cache.put("Q1", {"name": "Entity 1"})
        cache.put("Q2", {"name": "Entity 2"})

        if hasattr(cache, 'clear'):
            cache.clear()
            assert len(cache.cache) == 0

    def test_cache_size(self):
        """Test getting cache size."""
        cache = EntityReferenceCache()

        cache.put("Q1", {"name": "Entity 1"})
        cache.put("Q2", {"name": "Entity 2"})
        cache.put("Q3", {"name": "Entity 3"})

        if hasattr(cache, 'size'):
            assert cache.size() == 3
        else:
            assert len(cache.cache) == 3

    def test_update_existing_entry(self):
        """Test updating an existing cache entry."""
        cache = EntityReferenceCache()

        cache.put("Q1", {"name": "Old Name"})
        cache.put("Q1", {"name": "New Name"})

        result = cache.get("Q1")
        assert result["name"] == "New Name"

    def test_corrupted_cache_file(self):
        """Test handling of corrupted cache file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pkl', delete=False) as f:
            cache_file = f.name
            f.write("corrupted data")

        try:
            # Should handle gracefully and start with empty cache
            cache = EntityReferenceCache(cache_file=cache_file)
            assert cache.cache == {}
        finally:
            Path(cache_file).unlink(missing_ok=True)

    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly."""
        cache = EntityReferenceCache()

        # Add data
        cache.put("Q1", {"name": "Entity 1"})

        # Generate hits and misses
        cache.get("Q1")  # hit
        cache.get("Q1")  # hit
        cache.get("Q2")  # miss
        cache.get("Q3")  # miss
        cache.get("Q1")  # hit

        assert cache.stats['hits'] == 3
        assert cache.stats['misses'] == 2
        assert cache.get_hit_rate() == pytest.approx(0.6, 0.01)
