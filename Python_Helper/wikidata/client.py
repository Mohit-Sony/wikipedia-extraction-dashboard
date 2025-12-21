"""
Wikidata API Client

Provides a robust client for fetching entity data from Wikidata's EntityData API.
Includes retry logic, rate limiting, TTL caching, and comprehensive error handling.
"""

import logging
import time
import requests
from typing import Optional, Dict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter to control API request frequency."""

    def __init__(self, requests_per_second: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests allowed per second
        """
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0

    def wait(self):
        """Wait if necessary to respect rate limit."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.min_interval:
            sleep_time = self.min_interval - time_since_last_request
            time.sleep(sleep_time)

        self.last_request_time = time.time()


class WikidataClient:
    """
    Client for fetching entity data from Wikidata EntityData API.

    Features:
        - Automatic retry with exponential backoff
        - Rate limiting to respect API guidelines
        - Proper error handling and logging
        - Session management for connection pooling
    """

    BASE_URL = "https://www.wikidata.org/wiki/Special:EntityData"
    USER_AGENT = "WikipediaExtractionPipeline/2.0 (Educational Research; Python/requests)"

    def __init__(
        self,
        timeout: int = 10,
        max_retries: int = 3,
        requests_per_second: float = 1.0,
        cache_ttl: int = 3600,
        cache_maxsize: int = 1000
    ):
        """
        Initialize Wikidata API client.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            requests_per_second: Rate limit for API requests
            cache_ttl: Time-to-live for cache entries in seconds (default 1 hour)
            cache_maxsize: Maximum number of entries in cache
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(requests_per_second)

        # TTL cache for API responses (Phase 4 Step 11 optimization)
        self.request_cache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)

        # Performance metrics
        self.metrics = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_fetch_time': 0.0,
            'errors': 0
        }

        # Create session with retry strategy
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,  # 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set headers
        self.session.headers.update({
            'User-Agent': self.USER_AGENT,
            'Accept': 'application/json'
        })

        logger.info(
            f"WikidataClient initialized: timeout={timeout}s, max_retries={max_retries}, "
            f"cache_ttl={cache_ttl}s, cache_maxsize={cache_maxsize}"
        )

    def fetch_entity_data(self, qid: str) -> Optional[Dict]:
        """
        Fetch entity data from Wikidata with retry logic and TTL caching.

        Args:
            qid: Wikidata entity ID (e.g., 'Q1001')

        Returns:
            Dictionary containing entity data, or None if fetch fails

        Example:
            >>> client = WikidataClient()
            >>> data = client.fetch_entity_data('Q1001')
            >>> data['entities']['Q1001']['labels']['en']['value']
            'Mahatma Gandhi'
        """
        if not qid or not qid.startswith('Q'):
            logger.error(f"Invalid QID format: {qid}")
            return None

        start_time = time.time()

        try:
            # Check TTL cache first (Phase 4 Step 11 optimization)
            if qid in self.request_cache:
                self.metrics['cache_hits'] += 1
                logger.debug(f"Cache hit for {qid}")
                return self.request_cache[qid]

            self.metrics['cache_misses'] += 1

            # Apply rate limiting
            self.rate_limiter.wait()

            # Make request
            response = self._make_request(qid)

            if response is None:
                self.metrics['errors'] += 1
                return None

            # Validate response
            if not self._validate_response(response, qid):
                self.metrics['errors'] += 1
                return None

            # Cache successful response
            self.request_cache[qid] = response

            # Update metrics
            fetch_time = time.time() - start_time
            self.metrics['total_fetch_time'] += fetch_time
            self.metrics['api_calls'] += 1

            logger.debug(f"Successfully fetched data for {qid} in {fetch_time:.2f}s")
            return response

        except Exception as e:
            logger.error(f"Unexpected error fetching {qid}: {e}")
            self.metrics['errors'] += 1
            return None

    def _make_request(self, qid: str) -> Optional[Dict]:
        """
        Make HTTP request to Wikidata API.

        Args:
            qid: Wikidata entity ID

        Returns:
            JSON response as dictionary, or None if request fails
        """
        url = f"{self.BASE_URL}/{qid}.json"

        try:
            logger.debug(f"Fetching {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # Parse JSON
            try:
                data = response.json()
                return data
            except ValueError as e:
                logger.error(f"Invalid JSON response for {qid}: {e}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching {qid} (timeout={self.timeout}s)")
            return None

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Entity {qid} not found (404)")
            elif e.response.status_code == 429:
                logger.warning(f"Rate limit exceeded for {qid}, retrying with backoff")
            else:
                logger.error(f"HTTP error fetching {qid}: {e}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching {qid}: {e}")
            return None

    def _validate_response(self, response: Dict, qid: str) -> bool:
        """
        Validate Wikidata API response.

        Args:
            response: JSON response dictionary
            qid: Expected entity ID

        Returns:
            True if response is valid, False otherwise
        """
        if not response:
            logger.error(f"Empty response for {qid}")
            return False

        if 'entities' not in response:
            logger.error(f"Missing 'entities' field in response for {qid}")
            return False

        entities = response.get('entities', {})

        if qid not in entities:
            # Check for redirects
            if len(entities) == 1:
                redirect_qid = list(entities.keys())[0]
                logger.info(f"Entity {qid} redirects to {redirect_qid}")
                # Update response to use correct QID
                return True
            else:
                logger.error(f"Entity {qid} not found in response")
                return False

        # Check if entity was deleted/missing
        entity_data = entities.get(qid, entities.get(list(entities.keys())[0]))
        if entity_data.get('missing') == '':
            logger.warning(f"Entity {qid} exists but has no data (deleted/missing)")
            return False

        return True

    def fetch_multiple_entities(self, qids: list) -> Dict[str, Dict]:
        """
        Fetch multiple entities in batches.

        Wikidata API supports fetching up to 50 entities per request.

        Args:
            qids: List of Wikidata entity IDs

        Returns:
            Dictionary mapping QID to entity data

        Example:
            >>> client = WikidataClient()
            >>> data = client.fetch_multiple_entities(['Q1001', 'Q1156'])
            >>> len(data)
            2
        """
        results = {}

        # Process in batches of 50
        batch_size = 50
        for i in range(0, len(qids), batch_size):
            batch = qids[i:i + batch_size]

            try:
                # Apply rate limiting
                self.rate_limiter.wait()

                # Build URL with multiple IDs
                ids_param = '|'.join(batch)
                url = f"{self.BASE_URL}.json?ids={ids_param}"

                logger.debug(f"Fetching batch of {len(batch)} entities")
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()

                data = response.json()
                entities = data.get('entities', {})

                # Add to results
                for qid in batch:
                    if qid in entities:
                        results[qid] = {'entities': {qid: entities[qid]}}
                    else:
                        logger.warning(f"Entity {qid} not in batch response")

            except Exception as e:
                logger.error(f"Error fetching batch {batch}: {e}")
                # Fall back to individual fetches
                for qid in batch:
                    entity_data = self.fetch_entity_data(qid)
                    if entity_data:
                        results[qid] = entity_data

        logger.info(f"Fetched {len(results)} out of {len(qids)} entities")
        return results

    def get_metrics(self) -> Dict:
        """
        Get performance metrics.

        Returns:
            Dictionary with performance statistics

        Example:
            >>> client.get_metrics()
            {
                'api_calls': 50,
                'cache_hits': 30,
                'cache_misses': 20,
                'cache_hit_rate': 0.6,
                'avg_fetch_time': 1.23,
                'errors': 2
            }
        """
        total_requests = self.metrics['cache_hits'] + self.metrics['cache_misses']
        cache_hit_rate = (
            self.metrics['cache_hits'] / total_requests
            if total_requests > 0 else 0.0
        )
        avg_fetch_time = (
            self.metrics['total_fetch_time'] / self.metrics['api_calls']
            if self.metrics['api_calls'] > 0 else 0.0
        )

        return {
            'api_calls': self.metrics['api_calls'],
            'cache_hits': self.metrics['cache_hits'],
            'cache_misses': self.metrics['cache_misses'],
            'cache_hit_rate': cache_hit_rate,
            'avg_fetch_time': avg_fetch_time,
            'errors': self.metrics['errors'],
            'cache_size': len(self.request_cache)
        }

    def log_metrics(self):
        """Log performance metrics to logger."""
        metrics = self.get_metrics()
        logger.info("=" * 50)
        logger.info("Wikidata Client Performance Metrics")
        logger.info("=" * 50)
        logger.info(f"API Calls:        {metrics['api_calls']}")
        logger.info(f"Cache Hits:       {metrics['cache_hits']}")
        logger.info(f"Cache Misses:     {metrics['cache_misses']}")
        logger.info(f"Cache Hit Rate:   {metrics['cache_hit_rate']:.2%}")
        logger.info(f"Cache Size:       {metrics['cache_size']}")
        logger.info(f"Avg Fetch Time:   {metrics['avg_fetch_time']:.3f}s")
        logger.info(f"Errors:           {metrics['errors']}")
        logger.info("=" * 50)

    def reset_metrics(self):
        """Reset performance metrics to zero."""
        self.metrics = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_fetch_time': 0.0,
            'errors': 0
        }
        logger.info("Performance metrics reset")

    def close(self):
        """Close the session and cleanup resources."""
        if self.session:
            # Log final metrics before closing
            self.log_metrics()
            self.session.close()
            logger.info("WikidataClient session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
