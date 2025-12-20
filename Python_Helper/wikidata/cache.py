"""
Entity Reference Cache

Provides caching for Wikidata entity references to prevent duplicate API calls
and improve performance. Supports thread-safe operations and disk persistence.
"""

import logging
import pickle
import threading
import time
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EntityReferenceCache:
    """
    Thread-safe cache for Wikidata entity references.

    Stores minimal entity data (QID, name, description, type) to avoid
    duplicate API calls when entities are referenced multiple times.

    Features:
        - Thread-safe get/put operations
        - Disk persistence with pickle
        - Cache statistics (hit rate tracking)
        - Automatic backup and corruption recovery
    """

    def __init__(self, cache_file: Optional[str] = None, auto_save_interval: int = 100):
        """
        Initialize entity reference cache.

        Args:
            cache_file: Path to pickle file for persistence (optional)
            auto_save_interval: Save to disk every N operations
        """
        self.cache: Dict[str, Dict] = {}
        self.cache_file = Path(cache_file) if cache_file else None
        self.lock = threading.Lock()
        self.auto_save_interval = auto_save_interval
        self.operations_since_save = 0

        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "puts": 0,
            "total_operations": 0
        }

        # Load from disk if file exists
        if self.cache_file and self.cache_file.exists():
            self._load_from_disk()

        logger.info(f"EntityReferenceCache initialized (cache_file={cache_file})")

    def get(self, qid: str) -> Optional[Dict]:
        """
        Get entity from cache.

        Args:
            qid: Wikidata entity ID (e.g., 'Q1001')

        Returns:
            Dictionary with entity data, or None if not in cache

        Example:
            >>> cache = EntityReferenceCache()
            >>> cache.put('Q1001', {'name': 'Gandhi', ...})
            >>> entity = cache.get('Q1001')
            >>> entity['name']
            'Gandhi'
        """
        with self.lock:
            self.stats['total_operations'] += 1

            if qid in self.cache:
                self.stats['hits'] += 1
                logger.debug(f"Cache hit for {qid}")
                return self.cache[qid].copy()  # Return copy to prevent external modification
            else:
                self.stats['misses'] += 1
                logger.debug(f"Cache miss for {qid}")
                return None

    def put(self, qid: str, entity_data: Dict):
        """
        Add entity to cache.

        Args:
            qid: Wikidata entity ID
            entity_data: Dictionary with entity information
                        {
                            'qid': 'Q1001',
                            'name': 'Entity Name',
                            'description': 'Brief description',
                            'type': 'human',
                            'key_data': {...}  # Optional minimal data
                        }

        Example:
            >>> cache = EntityReferenceCache()
            >>> cache.put('Q1001', {
            ...     'qid': 'Q1001',
            ...     'name': 'Mahatma Gandhi',
            ...     'description': 'Indian independence activist',
            ...     'type': 'human'
            ... })
        """
        with self.lock:
            # Add timestamp
            entity_data['cached_at'] = datetime.now().isoformat()

            self.cache[qid] = entity_data
            self.stats['puts'] += 1
            self.stats['total_operations'] += 1
            self.operations_since_save += 1

            logger.debug(f"Cached entity {qid}")

            # Auto-save periodically
            if self.cache_file and self.operations_since_save >= self.auto_save_interval:
                self._save_to_disk()
                self.operations_since_save = 0

    def _load_from_disk(self):
        """Load cache from pickle file."""
        if not self.cache_file or not self.cache_file.exists():
            logger.warning(f"Cache file not found: {self.cache_file}")
            return

        try:
            with open(self.cache_file, 'rb') as f:
                data = pickle.load(f)

            # Validate loaded data
            if isinstance(data, dict) and 'cache' in data and 'stats' in data:
                self.cache = data['cache']
                self.stats = data['stats']
                logger.info(f"Loaded {len(self.cache)} entities from cache file")
            else:
                logger.warning("Invalid cache file format, starting fresh")
                self.cache = {}

        except Exception as e:
            logger.error(f"Failed to load cache from {self.cache_file}: {e}")

            # Try to load backup if available
            backup_file = Path(str(self.cache_file) + '.backup')
            if backup_file.exists():
                logger.info("Attempting to load from backup...")
                try:
                    with open(backup_file, 'rb') as f:
                        data = pickle.load(f)
                    self.cache = data.get('cache', {})
                    self.stats = data.get('stats', self.stats)
                    logger.info(f"Loaded {len(self.cache)} entities from backup")
                except Exception as backup_error:
                    logger.error(f"Backup also failed: {backup_error}")
                    self.cache = {}

    def _save_to_disk(self):
        """Save cache to pickle file."""
        if not self.cache_file:
            return

        try:
            # Create directory if it doesn't exist
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Create backup of existing file
            if self.cache_file.exists():
                backup_file = Path(str(self.cache_file) + '.backup')
                try:
                    import shutil
                    shutil.copy2(self.cache_file, backup_file)
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")

            # Save cache
            data = {
                'cache': self.cache,
                'stats': self.stats,
                'saved_at': datetime.now().isoformat(),
                'version': '1.0'
            }

            with open(self.cache_file, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.debug(f"Saved cache to {self.cache_file} ({len(self.cache)} entities)")

        except Exception as e:
            logger.error(f"Failed to save cache to {self.cache_file}: {e}")

    def get_hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            Hit rate as a decimal (0.0 to 1.0)

        Example:
            >>> cache = EntityReferenceCache()
            >>> cache.put('Q1', {'name': 'Test'})
            >>> cache.get('Q1')  # hit
            >>> cache.get('Q2')  # miss
            >>> cache.get_hit_rate()
            0.5
        """
        total_lookups = self.stats['hits'] + self.stats['misses']
        if total_lookups == 0:
            return 0.0

        return self.stats['hits'] / total_lookups

    def get_statistics(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with statistics

        Example:
            >>> cache = EntityReferenceCache()
            >>> stats = cache.get_statistics()
            >>> stats['size']
            0
        """
        hit_rate = self.get_hit_rate()

        return {
            'size': len(self.cache),
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'puts': self.stats['puts'],
            'hit_rate': hit_rate,
            'total_operations': self.stats['total_operations']
        }

    def clear(self):
        """Clear all cached entities."""
        with self.lock:
            self.cache.clear()
            logger.info("Cache cleared")

    def remove(self, qid: str) -> bool:
        """
        Remove entity from cache.

        Args:
            qid: Entity ID to remove

        Returns:
            True if entity was removed, False if not in cache
        """
        with self.lock:
            if qid in self.cache:
                del self.cache[qid]
                logger.debug(f"Removed {qid} from cache")
                return True
            return False

    def contains(self, qid: str) -> bool:
        """
        Check if entity is in cache without affecting statistics.

        Args:
            qid: Entity ID to check

        Returns:
            True if entity is in cache, False otherwise
        """
        with self.lock:
            return qid in self.cache

    def save(self):
        """Manually trigger save to disk."""
        with self.lock:
            self._save_to_disk()
            self.operations_since_save = 0

    def __len__(self) -> int:
        """Return number of cached entities."""
        return len(self.cache)

    def __contains__(self, qid: str) -> bool:
        """Support 'in' operator."""
        return self.contains(qid)

    def __del__(self):
        """Destructor - save cache before cleanup."""
        if self.cache_file and self.operations_since_save > 0:
            try:
                self._save_to_disk()
            except Exception as e:
                logger.error(f"Failed to save cache in destructor: {e}")
