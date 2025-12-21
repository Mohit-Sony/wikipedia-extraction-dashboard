#!/usr/bin/env python3
"""
Optimized Wikipedia Data Extractor

A high-performance Wikipedia data extraction system with:
- Concurrent processing
- API request batching
- Comprehensive error handling
- Detailed logging
- Caching support
- Memory optimization

Usage:
    python optimized_wikipedia_extractor.py "Page Title"
    python optimized_wikipedia_extractor.py "Albert Einstein" --format json --cache-dir ./cache
"""

import asyncio
import aiohttp
import logging
import json
import csv
import re
import argparse
import hashlib
import time
from pathlib import Path
from urllib.parse import unquote, urlparse
from bs4 import BeautifulSoup
import pandas as pd
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pickle
from datetime import datetime, timedelta
import sys
from typing import Any, Dict, Optional
from urllib.parse import quote

# Wikidata integration
try:
    from Python_Helper.wikidata_integration import WikidataIntegration, WikidataIntegrationConfig
    WIKIDATA_AVAILABLE = True
except ImportError:
    try:
        # Try relative import if running from Python_Helper directory
        from wikidata_integration import WikidataIntegration, WikidataIntegrationConfig
        WIKIDATA_AVAILABLE = True
    except ImportError:
        WIKIDATA_AVAILABLE = False
        logging.warning("WikidataIntegration not available - structured data enrichment will be skipped")

# Configure comprehensive logging
def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Setup comprehensive logging with file and console handlers"""
    logger = logging.getLogger("WikipediaExtractor")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.error(f"Failed to setup file logging: {e}")
    
    return logger

@dataclass
class ExtractionConfig:
    """Configuration for extraction process"""
    max_concurrent_requests: int = 10
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    cache_ttl_hours: int = 24
    max_chunk_length: int = 1000
    batch_size: int = 50
    enable_caching: bool = True
    user_agent: str = "WikipediaExtractor/2.0 (Educational/Research; Contact: your-email@example.com)"

class CacheManager:
    """File-based caching system with TTL support"""
    
    def __init__(self, cache_dir: str, ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
        self.logger = logging.getLogger("WikipediaExtractor.Cache")
        
    def _get_cache_path(self, key: str) -> Path:
        """Generate cache file path from key"""
        try:
            hash_key = hashlib.md5(key.encode()).hexdigest()
            return self.cache_dir / f"{hash_key}.cache"
        except Exception as e:
            self.logger.error(f"Error generating cache path for key '{key}': {e}")
            raise
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if exists and not expired"""
        try:
            cache_path = self._get_cache_path(key)
            
            if not cache_path.exists():
                self.logger.debug(f"Cache miss: {key}")
                return None
            
            # Check if cache is expired
            if datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime) > self.ttl:
                self.logger.debug(f"Cache expired: {key}")
                cache_path.unlink(missing_ok=True)
                return None
            
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
                self.logger.debug(f"Cache hit: {key}")
                return data
                
        except Exception as e:
            self.logger.error(f"Error reading cache for key '{key}': {e}")
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """Store value in cache"""
        try:
            cache_path = self._get_cache_path(key)
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
            self.logger.debug(f"Cached: {key}")
            return True
        except Exception as e:
            self.logger.error(f"Error writing cache for key '{key}': {e}")
            return False
    
    def clear_expired(self) -> int:
        """Clear expired cache entries"""
        cleared = 0
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                if datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime) > self.ttl:
                    cache_file.unlink()
                    cleared += 1
            #self.logger.info(f"Cleared {cleared} expired cache entries")
        except Exception as e:
            self.logger.error(f"Error clearing expired cache: {e}")
        return cleared

class APIClient:
    """Async HTTP client with retry logic and rate limiting"""
    
    def __init__(self, config: ExtractionConfig):
        self.config = config
        self.logger = logging.getLogger("WikipediaExtractor.APIClient")
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        
    async def __aenter__(self):
        """Async context manager entry"""
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={'User-Agent': self.config.user_agent}
            )
            self.logger.debug("API client session created")
            return self
        except Exception as e:
            self.logger.error(f"Error creating API client session: {e}")
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            try:
                await self.session.close()
                self.logger.debug("API client session closed")
            except Exception as e:
                self.logger.error(f"Error closing API client session: {e}")
    
    async def get_json(self, url: str, params: Dict = None, cache_key: str = None) -> Optional[Dict]:
        """Make GET request with retry logic and caching"""
        async with self.semaphore:
            for attempt in range(self.config.max_retries + 1):
                try:
                    self.logger.debug(f"GET request (attempt {attempt + 1}): {url}")
                    
                    async with self.session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.logger.debug(f"Successful response from {url}")
                            return data
                        elif response.status == 429:  # Rate limited
                            wait_time = min(2 ** attempt, 60)
                            self.logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            self.logger.warning(f"HTTP {response.status} from {url}")
                            
                except asyncio.TimeoutError:
                    self.logger.warning(f"Timeout for {url} (attempt {attempt + 1})")
                except Exception as e:
                    self.logger.error(f"Request error for {url} (attempt {attempt + 1}): {e}")
                
                if attempt < self.config.max_retries:
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    await asyncio.sleep(wait_time)
            
            self.logger.error(f"All retry attempts failed for {url}")
            return None

class WikidataAPI:
    """Specialized Wikidata API client"""
    
    def __init__(self, api_client: APIClient, cache: Optional[CacheManager] = None):
        self.api_client = api_client
        self.cache = cache
        self.logger = logging.getLogger("WikipediaExtractor.WikidataAPI")
        
    async def get_entity_types_batch(self, qids: List[str]) -> Dict[str, Optional[str]]:
        """Get entity types for multiple QIDs in batch"""
        if not qids:
            return {}
            
        #self.logger.info(f"Fetching entity types for {len(qids)} QIDs")
        results = {}
        
        # Check cache first
        uncached_qids = []
        if self.cache:
            for qid in qids:
                cached_type = self.cache.get(f"wikidata_type_{qid}")
                if cached_type is not None:
                    results[qid] = cached_type
                else:
                    uncached_qids.append(qid)
        else:
            uncached_qids = qids
        
        if not uncached_qids:
            self.logger.debug("All QIDs found in cache")
            return results
        
        # Process uncached QIDs in batches
        batch_size = 50  # Wikidata API limit
        for i in range(0, len(uncached_qids), batch_size):
            batch = uncached_qids[i:i + batch_size]
            try:
                batch_results = await self._fetch_entity_types_batch(batch)
                results.update(batch_results)
                
                # Cache results
                if self.cache:
                    for qid, entity_type in batch_results.items():
                        self.cache.set(f"wikidata_type_{qid}", entity_type)
                        
            except Exception as e:
                self.logger.error(f"Error fetching batch {i//batch_size + 1}: {e}")
                # Fill with None for failed QIDs
                for qid in batch:
                    if qid not in results:
                        results[qid] = None
        
        return results
    
    # async def _fetch_entity_types_batchV1(self, qids: List[str]) -> Dict[str, Optional[str]]:
    #     """Fetch entity types for a batch of QIDs"""
    #     try:
    #         qid_string = "|".join(qids)
    #         url = f"https://www.wikidata.org/wiki/Special:EntityData/{qids[0]}.json"
            
    #         # For batch requests, we need to use the API endpoint
    #         params = {
    #             'action': 'wbgetentities',
    #             'ids': qid_string,
    #             'props': 'claims',
    #             'format': 'json'
    #         }
            
    #         data = await self.api_client.get_json(
    #             "https://www.wikidata.org/w/api.php", 
    #             params=params
    #         )
            
    #         if not data or 'entities' not in data:
    #             self.logger.warning(f"No entities data for QIDs: {qids}")
    #             return {qid: None for qid in qids}
            
    #         results = {}
    #         for qid in qids:
    #             try:
    #                 entity = data['entities'].get(qid, {})
    #                 if 'missing' in entity:
    #                     results[qid] = None
    #                     continue
                    
    #                 claims = entity.get('claims', {})
    #                 instance_of = claims.get('P31', [])
                    
    #                 if instance_of:
    #                     value = instance_of[0].get('mainsnak', {}).get('datavalue', {}).get('value', {})
    #                     type_qid = value.get('id')
                        
    #                     if type_qid:
    #                         # Get the label for this type (simplified - could be cached separately)
    #                         type_mapping = {
    #                             'Q5': 'human',
    #                             'Q16334295': 'group of humans',
    #                             'Q43229': 'organization',
    #                             'Q6256': 'country',
    #                             'Q515': 'city',
    #                             'Q3624078': 'sovereign state',
    #                             'Q618123': 'geographical object'
    #                         }
    #                         results[qid] = type_mapping.get(type_qid, 'entity')
    #                     else:
    #                         results[qid] = None
    #                 else:
    #                     results[qid] = None
                        
    #             except Exception as e:
    #                 self.logger.error(f"Error processing entity {qid}: {e}")
    #                 results[qid] = None
            
    #         return results
            
    #     except Exception as e:
    #         self.logger.error(f"Error in batch entity type fetch: {e}")
    #         return {qid: None for qid in qids}

    async def _fetch_entity_types_batch(self, qids: List[str]) -> Dict[str, Optional[str]]:
        """Fetch entity types for a batch of QIDs, resolving instance-of QIDs to labels"""
        try:
            qid_string = "|".join(qids)
            params = {
                "action": "wbgetentities",
                "ids": qid_string,
                "props": "claims",
                "format": "json"
            }

            data = await self.api_client.get_json(
                "https://www.wikidata.org/w/api.php",
                params=params
            )

            if not data or "entities" not in data:
                self.logger.warning(f"No entities data for QIDs: {qids}")
                return {qid: None for qid in qids}

            results = {}
            type_qids = {}  # qid → type_qid

            # Step 1: extract type_qids for all input QIDs
            for qid in qids:
                try:
                    entity = data["entities"].get(qid, {})
                    if "missing" in entity:
                        results[qid] = None
                        continue

                    claims = entity.get("claims", {})
                    instance_of = claims.get("P31", [])

                    if instance_of:
                        value = (
                            instance_of[0]
                            .get("mainsnak", {})
                            .get("datavalue", {})
                            .get("value", {})
                        )
                        type_qid = value.get("id")
                        if type_qid:
                            type_qids[qid] = type_qid
                        else:
                            results[qid] = None
                    else:
                        results[qid] = None

                except Exception as e:
                    self.logger.error(f"Error processing entity {qid}: {e}")
                    results[qid] = None

            if not type_qids:
                return results

            # Step 2: fetch labels for all type_qids in bulk
            type_qid_string = "|".join(set(type_qids.values()))
            label_params = {
                "action": "wbgetentities",
                "ids": type_qid_string,
                "props": "labels",
                "languages": "en",
                "format": "json",
            }

            label_data = await self.api_client.get_json(
                "https://www.wikidata.org/w/api.php", params=label_params
            )

            type_labels = {}
            if label_data and "entities" in label_data:
                for tqid, info in label_data["entities"].items():
                    label = info.get("labels", {}).get("en", {}).get("value")
                    if label:
                        type_labels[tqid] = label.lower()  # normalize to lowercase

            # Step 3: map back type labels to original qids
            for qid, tqid in type_qids.items():
                results[qid] = type_labels.get(tqid, None)

            return results

        except Exception as e:
            self.logger.error(f"Error in batch entity type fetch: {e}")
            return {qid: None for qid in qids}

class OptimizedWikipediaExtractor:
    """Main extractor class with all optimizations"""
    
    def __init__(self, config: ExtractionConfig = None, cache_dir: str = "./cache"):
        self.config = config or ExtractionConfig()
        self.cache = CacheManager(cache_dir, self.config.cache_ttl_hours) if self.config.enable_caching else None
        self.logger = logging.getLogger("WikipediaExtractor.Main")
        self.api_url = "https://en.wikipedia.org/w/api.php"
        self.base_url = "https://en.wikipedia.org/api/rest_v1"

        # Initialize Wikidata integration
        self.wikidata_integration = None
        if WIKIDATA_AVAILABLE:
            try:
                wikidata_config = WikidataIntegrationConfig(
                    enable_enrichment=True,
                    config_dir="../config/properties",  # Relative to Python_Helper directory
                    cache_file="../pipeline_state/entity_cache.pkl",
                    cache_ttl=3600,
                    cache_maxsize=1000
                )
                self.wikidata_integration = WikidataIntegration(config=wikidata_config)
                self.logger.info("Wikidata enrichment enabled")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Wikidata integration: {e}")
                self.wikidata_integration = None
        else:
            self.logger.info("Wikidata enrichment disabled (module not available)")
        
    async def extract_page_data(self, page_title: str) -> Dict[str, Any]:
        """Extract comprehensive data from a Wikipedia page with optimizations"""
        self.logger.info(f"Starting extraction for: {page_title}")
        start_time = time.time()
        
        data = {
            'title': page_title,
            'content': {},
            'links': {},
            'tables': [],
            'images': [],
            'references': [],
            'categories': [],
            'infobox': {},
            'metadata': {},
            'qid': None,
            'type': None,
            'revId': None,
            'wikitext': None,
            'chunks': [],
            'extraction_metadata': {
                'timestamp': datetime.now().isoformat(),
                'extractor_version': '2.0',
                'extraction_time': 0
            }
        }
        
        try:
            async with APIClient(self.config) as api_client:
                wikidata_api = WikidataAPI(api_client, self.cache)
                
                # Parallel extraction of basic data
                #self.logger.info("Extracting basic page data...")
                basic_tasks = [
                    self._get_page_content(api_client, page_title),
                    self._get_page_metadata(api_client, page_title),
                    self._get_page_extended_info(api_client, page_title),
                    self._get_page_categories(api_client, page_title)
                ]
                
                basic_results = await asyncio.gather(*basic_tasks, return_exceptions=True)
                
                # Process basic results
                for i, result in enumerate(basic_results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Basic extraction task {i} failed: {result}")
                        continue
                    
                    if i == 0 and result:  # content
                        data['content'] = result
                    elif i == 1 and result:  # metadata
                        data['metadata'] = result
                    elif i == 2 and result:  # extended info
                        data.update(result)
                    elif i == 3 and result:  # categories
                        data['categories'] = result
                
                # Extract HTML-dependent data
                #self.logger.info("Extracting HTML-dependent data...")
                html_content = await self._get_page_html(api_client, page_title)
                if html_content:
                    try:
                        data['tables'] = self._extract_tables(html_content)
                        data['infobox'] = self._extract_infobox(html_content)
                        data['references'] = self._extract_references(html_content)
                    except Exception as e:
                        self.logger.error(f"HTML processing error: {e}")
                
                # Extract and enrich links
                #self.logger.info("Extracting and enriching links...")
                try:
                    links_data = await self._get_page_links_optimized(api_client, wikidata_api, page_title)
                    data['links'] = links_data
                except Exception as e:
                    self.logger.error(f"Links extraction error: {e}")
                    data['links'] = {'internal_links': [], 'external_links': []}
                
                # Extract images
                #self.logger.info("Extracting images...")
                try:
                    data['images'] = await self._get_page_images_optimized(api_client, page_title)
                except Exception as e:
                    self.logger.error(f"Images extraction error: {e}")
                    data['images'] = []
                
                # Generate chunks
                #self.logger.info("Generating content chunks...")
                try:
                    if html_content:
                        data['chunks'] = await self._extract_chunks_optimized(
                            html_content, page_title, data.get('qid'), 
                            data.get('type'), data['links'].get('internal_links', [])
                        )
                except Exception as e:
                    self.logger.error(f"Chunk extraction error: {e}")
                    data['chunks'] = []
                
                # Remove Duplicate links from internal links 
                # _deduplicate_links_by_qid
                try:
                    if data['links'] and data['links']['internal_links'] and len(data['links']['internal_links'])>0 :
                        deduplicated_links = self._deduplicate_links_by_qid(data['links']['internal_links'])
                        data['links']['internal_links'] = deduplicated_links

                except Exception as e:
                    self.logger.error(f"Deduplication Error: {e}")

                # Add entity type if we have QID but no type
                if data.get('qid') and not data.get('type'):
                    try:
                        types = await wikidata_api.get_entity_types_batch([data['qid']])
                        data['type'] = types.get(data['qid'])
                    except Exception as e:
                        self.logger.error(f"Entity type extraction error: {e}")
                
                extraction_time = time.time() - start_time
                data['extraction_metadata']['extraction_time'] = round(extraction_time, 2)

                #self.logger.info(f"Extraction completed in {extraction_time:.2f}s")
                self._log_extraction_summary(data)

                # Enrich with Wikidata structured data
                if self.wikidata_integration and data.get('qid'):
                    try:
                        self.logger.info(f"Enriching with Wikidata structured data for QID: {data['qid']}")
                        enriched_data = self.wikidata_integration.enrich(data, data['qid'])
                        if enriched_data:
                            data = enriched_data
                            self.logger.info("Wikidata enrichment completed successfully")
                        else:
                            self.logger.warning("Wikidata enrichment returned no data")
                    except Exception as e:
                        self.logger.warning(f"Wikidata enrichment failed (continuing with Wikipedia data): {e}")

                return data
                
        except Exception as e:
            self.logger.error(f"Fatal error during extraction: {e}")
            data['extraction_metadata']['extraction_time'] = time.time() - start_time
            data['extraction_metadata']['error'] = str(e)
            return data
    
    def _log_extraction_summary(self, data: Dict[str, Any]):
        """Log extraction summary statistics"""
        try:
            #self.logger.info("=== Extraction Summary ===")
            self.logger.info(f"Page: {data['title']}")
            #self.logger.info(f"QID: {data.get('qid', 'Not found')}")
            #self.logger.info(f"Type: {data.get('type', 'Unknown')}")
            #self.logger.info(f"Content length: {len(data['content'].get('extract', ''))}")
            #self.logger.info(f"Internal links: {len(data['links'].get('internal_links', []))}")
            #self.logger.info(f"External links: {len(data['links'].get('external_links', []))}")
            #self.logger.info(f"Images: {len(data['images'])}")
            #self.logger.info(f"Tables: {len(data['tables'])}")
            #self.logger.info(f"Categories: {len(data['categories'])}")
            #self.logger.info(f"References: {len(data['references'])}")
            #self.logger.info(f"Chunks: {len(data['chunks'])}")
            #self.logger.info(f"Extraction time: {data['extraction_metadata']['extraction_time']}s")
        except Exception as e:
            self.logger.error(f"Error logging summary: {e}")
    
    async def _get_page_contentV1(self, api_client: APIClient, page_title: str) -> Dict[str, Any]:
        """Get page content with caching and error handling"""
        cache_key = f"content_{page_title}"
        
        try:
            if self.cache:
                cached = self.cache.get(cache_key)
                if cached:
                    self.logger.debug(f"Content cache hit for {page_title}")
                    return cached
            
            # Get page summary
            summary_url = f"{self.base_url}/page/summary/{page_title.replace(' ', '_')}"
            summary_data = await api_client.get_json(summary_url) or {}
            
            # Get full page content
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'extracts',
                'exintro': False,
                'explaintext': True,
                'exsectionformat': 'plain'
            }
            
            data = await api_client.get_json(self.api_url, params=params)
            if not data or 'query' not in data:
                self.logger.warning(f"No content data for {page_title}")
                return {}
            
            page_id = list(data['query']['pages'].keys())[0]
            page_data = data['query']['pages'][page_id]
            
            content = {
                'extract': page_data.get('extract', ''),
                'summary': summary_data.get('extract', ''),
                'description': summary_data.get('description', ''),
                'page_id': page_id,
                'namespace': page_data.get('ns', 0)
            }
            
            if self.cache:
                self.cache.set(cache_key, content)
            
            return content
            
        except Exception as e:
            self.logger.error(f"Error getting page content for {page_title}: {e}")
            return {}
    async def _get_page_content(self, api_client: APIClient, page_title: str) -> Dict[str, Any]:
        """Get page content with caching and error handling."""
        cache_key = f"content_{page_title}"

        try:
            if self.cache:
                cached = self.cache.get(cache_key)
                # Use 'is not None' to avoid dropping valid-but-falsy cached payloads
                if cached is not None:
                    self.logger.debug(f"Content cache hit for {page_title}")
                    return cached

            # Normalize/encode title for REST endpoint
            rest_title = quote(page_title.replace(" ", "_"), safe="")

            # 1) REST summary (intro, short description, etc.)
            summary_url = f"{self.base_url}/page/summary/{rest_title}"
            summary_data = await api_client.get_json(summary_url) or {}

            # 2) Action API: full plaintext extract (follow redirects)
            # IMPORTANT: Use strings/ints only; do not pass booleans.
            params = {
                "action": "query",
                "format": "json",
                "titles": page_title,      # spaces are fine here; requests will encode
                "prop": "extracts",
                "explaintext": "1",        # was True → use "1"
                "exsectionformat": "plain",
                "redirects": "1"           # follow redirects
                # DO NOT send exintro=False; omit it if you want full content
            }

            data = await api_client.get_json(self.api_url, params=params)
            if not data or "query" not in data:
                self.logger.warning(f"No content data for {page_title}")
                # Still return what we have from REST summary (may be useful)
                content = {
                    "extract": "",
                    "summary": summary_data.get("extract", ""),
                    "description": summary_data.get("description", ""),
                    "page_id": None,
                    "namespace": None,
                }
                if self.cache:
                    self.cache.set(cache_key, content)
                return content

            pages = data.get("query", {}).get("pages", {})
            # Pick the first (and typically only) page entry
            page_data = next(iter(pages.values()), {})

            # If page missing, fall back to REST summary-only payload
            if page_data.get("missing"):
                self.logger.warning(f"Page missing for {page_title}")
                content = {
                    "extract": "",
                    "summary": summary_data.get("extract", ""),
                    "description": summary_data.get("description", ""),
                    "page_id": None,
                    "namespace": None,
                }
            else:
                content = {
                    "extract": page_data.get("extract", "") or "",
                    "summary": summary_data.get("extract", "") or "",
                    "description": summary_data.get("description", "") or "",
                    "page_id": page_data.get("pageid"),
                    "namespace": page_data.get("ns", 0),
                }

            if self.cache:
                self.cache.set(cache_key, content)

            return content

        except Exception as e:
            self.logger.error(f"Error getting page content for {page_title}: {e}")
            return {}
    async def _get_page_metadata(self, api_client: APIClient, page_title: str) -> Dict[str, Any]:
        """Get page metadata with error handling"""
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'info',
                'inprop': 'url|watchers|visitingwatchers|displaytitle'
            }
            
            data = await api_client.get_json(self.api_url, params=params)
            if not data or 'query' not in data:
                return {}
            
            page_id = list(data['query']['pages'].keys())[0]
            page_info = data['query']['pages'][page_id]
            
            return {
                'page_id': page_id,
                'title': page_info.get('title', ''),
                'url': page_info.get('fullurl', ''),
                'last_modified': page_info.get('touched', ''),
                'page_length': page_info.get('length', 0),
                'watchers': page_info.get('watchers', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting metadata for {page_title}: {e}")
            return {}
    
    async def _get_page_extended_info(self, api_client: APIClient, page_title: str) -> Dict[str, Any]:
        """Get extended page information"""
        try:
            params = {
                "action": "query",
                "titles": page_title,
                "prop": "revisions|pageprops",
                "rvprop": "ids|content",
                "rvslots": "main",
                "format": "json"
            }
            
            data = await api_client.get_json(self.api_url, params=params)
            if not data or 'query' not in data:
                return {}
            
            pages = data.get("query", {}).get("pages", {})
            if not pages:
                return {}
            
            page = next(iter(pages.values()))
            
            return {
                'qid': page.get("pageprops", {}).get("wikibase_item"),
                'title': page.get("title"),
                'revId': page.get("revisions", [{}])[0].get("revid"),
                'wikitext': (
                    page.get("revisions", [{}])[0]
                    .get("slots", {})
                    .get("main", {})
                    .get("*", "")[:10000]  # Limit wikitext size
                )
            }
            
        except Exception as e:
            self.logger.error(f"Error getting extended info for {page_title}: {e}")
            return {}
    
    async def _get_page_categories(self, api_client: APIClient, page_title: str) -> List[str]:
        """Get page categories with filtering"""
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'categories',
                'cllimit': 'max'
            }
            
            data = await api_client.get_json(self.api_url, params=params)
            if not data or 'query' not in data:
                return []
            
            page_id = list(data['query']['pages'].keys())[0]
            categories = data['query']['pages'][page_id].get('categories', [])
            
            # Filter out maintenance categories
            filtered_categories = []
            skip_patterns = [
                'Articles with', 'All articles', 'Pages with', 'Wikipedia',
                'Commons category', 'Template', 'User', 'Webarchive'
            ]
            
            for cat in categories:
                cat_title = cat['title']
                if not any(pattern in cat_title for pattern in skip_patterns):
                    filtered_categories.append(cat_title)
            
            return filtered_categories
            
        except Exception as e:
            self.logger.error(f"Error getting categories for {page_title}: {e}")
            return []
    
    async def _get_page_html(self, api_client: APIClient, page_title: str) -> Optional[str]:
        """Get HTML content with caching"""
        cache_key = f"html_{page_title}"
        
        try:
            if self.cache:
                cached = self.cache.get(cache_key)
                if cached:
                    return cached
            
            params = {
                'action': 'parse',
                'format': 'json',
                'page': page_title,
                'prop': 'text'
            }
            
            data = await api_client.get_json(self.api_url, params=params)
            if not data or 'parse' not in data:
                return None
            
            html_content = data.get('parse', {}).get('text', {}).get('*', '')
            
            if self.cache and html_content:
                self.cache.set(cache_key, html_content)
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Error getting HTML for {page_title}: {e}")
            return None
    
    async def _get_page_links_optimized(self, api_client: APIClient, wikidata_api: WikidataAPI, page_title: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get and enrich page links with batch processing"""
        try:
            internal_links = []
            external_links = []
            
            # Get internal links
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'links',
                'pllimit': 'max'
            }
            
            link_titles = []
            while True:
                data = await api_client.get_json(self.api_url, params=params)
                if not data or 'query' not in data:
                    break
                
                page_id = list(data['query']['pages'].keys())[0]
                page_data = data['query']['pages'][page_id]
                links = page_data.get('links', [])
                
                for link in links:
                    title = link.get("title")
                    if title and not title.startswith(('Category:', 'File:', 'Template:')):
                        link_titles.append(title)
                        internal_links.append({
                            "title": title,
                            "pageid": page_data.get("pageid"),
                            "ns": link.get("ns"),
                            "shortDesc":None,
                            "link": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                            "type": None,
                            "qid": None
                        })
                
                if 'continue' not in data:
                    break
                params.update(data['continue'])
            
            # Batch fetch QIDs for internal links
            if link_titles:
                #self.logger.info(f"Enriching {len(link_titles)} internal links...")
                qid_mapping = await self._get_qids_batch(api_client, link_titles)
                type_mapping = await wikidata_api.get_entity_types_batch(
                    [info["qid"] for info in qid_mapping.values()]
                )

                for link in internal_links:
                    info = qid_mapping.get(link["title"])
                    if info:
                        qid = info["qid"]
                        link["qid"] = qid
                        link["type"] = type_mapping.get(qid)
                        link["shortDesc"] = info.get("shortDesc")
                        link["redirectTitle"] = info.get("redirectTitle")
            
            # Get external links
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'extlinks',
                'ellimit': 'max'
            }
            
            data = await api_client.get_json(self.api_url, params=params)
            if data and 'query' in data:
                page_id = list(data['query']['pages'].keys())[0]
                page_data = data['query']['pages'][page_id]
                ext_links = page_data.get('extlinks', [])
                
                for link in ext_links[:100]:  # Limit external links
                    url = link.get("*")
                    if url:
                        external_links.append({
                            "title": None,
                            "pageid": None,
                            "ns": None,
                            "link": url,
                            "type": "external",
                            "qid": None
                        })
            
            return {
                'internal_links': internal_links,
                'external_links': external_links
            }
            
        except Exception as e:
            self.logger.error(f"Error getting links for {page_title}: {e}")
            return {'internal_links': [], 'external_links': []}
    
    async def _get_qids_batchV1(self, api_client: APIClient, titles: List[str]) -> Dict[str, str]:
        """Get QIDs for multiple page titles in batch"""
        if not titles:
            return {}
        
        try:
            qid_mapping = {}
            batch_size = 50
            
            for i in range(0, len(titles), batch_size):
                batch = titles[i:i + batch_size]
                #print("inside : get_qids_batch - Batch is  : ", "|".join(batch) )
                params = {
                    "action": "query",
                    "titles": "|".join(batch),
                    "prop": "pageprops",
                    "format": "json",
                    "redirects": 1
                }
                
                data = await api_client.get_json(self.api_url, params=params)
                if not data or 'query' not in data:
                    continue
                
                pages = data.get("query", {}).get("pages", {})
                #print("----- OUTPUT for batch query is : " ,  pages)
                for page_info in pages.values():
                    title = page_info.get("title")
                    qid = page_info.get("pageprops", {}).get("wikibase_item")
                    if title and qid:
                        qid_mapping[title] = qid
                
                # Small delay between batches
                await asyncio.sleep(0.1)
            
            return qid_mapping
            
        except Exception as e:
            self.logger.error(f"Error getting QIDs in batch: {e}")
            return {}
    
    async def _get_qids_batchV2(self, api_client: APIClient, titles: List[str]) -> Dict[str, str]:
        """Get QIDs for multiple page titles in batch, keeping only original input titles"""
        if not titles:
            return {}
        
        try:
            qid_mapping = {}
            batch_size = 50
            
            for i in range(0, len(titles), batch_size):
                batch = titles[i:i + batch_size]
                #print("inside : get_qids_batch - Batch is  : ", "|".join(batch))
                params = {
                    "action": "query",
                    "titles": "|".join(batch),
                    "prop": "pageprops",
                    "format": "json",
                    "redirects": 1
                }
                
                data = await api_client.get_json(self.api_url, params=params)
                if not data or 'query' not in data:
                    continue
                
                query = data.get("query", {})
                pages = query.get("pages", {})
                redirects = query.get("redirects", [])
                
                # Build redirect map: original → resolved
                redirect_map = {r["from"]: r["to"] for r in redirects}
                
                #print("----- OUTPUT for batch query is : ", pages)
                
                # For each input title, decide which resolved title to look up
                for title in batch:
                    resolved_title = redirect_map.get(title, title)
                    
                    # Find page info by resolved title
                    page_info = next(
                        (p for p in pages.values() if p.get("title") == resolved_title), 
                        None
                    )
                    if not page_info:
                        continue
                    
                    qid = page_info.get("pageprops", {}).get("wikibase_item")
                    if qid:
                        qid_mapping[title] = qid   # always use original title as key
                
                # Small delay between batches
                await asyncio.sleep(0.1)
            
            return qid_mapping
            
        except Exception as e:
            self.logger.error(f"Error getting QIDs in batch: {e}")
            return {}

    async def _get_qids_batch(self, api_client: APIClient, titles: List[str]) -> Dict[str, Dict[str, Optional[str]]]:
        """Get QIDs, short descriptions, and redirect titles for multiple page titles in batch."""
        if not titles:
            return {}
        
        try:
            qid_mapping = {}
            batch_size = 50
            
            for i in range(0, len(titles), batch_size):
                batch = titles[i:i + batch_size]
                # print("inside : get_qids_batch - Batch is  : ", "|".join(batch))
                params = {
                    "action": "query",
                    "titles": "|".join(batch),
                    "prop": "pageprops",
                    "format": "json",
                    "redirects": 1
                }
                
                data = await api_client.get_json(self.api_url, params=params)
                if not data or "query" not in data:
                    continue
                
                query = data.get("query", {})
                pages = query.get("pages", {})
                redirects = query.get("redirects", [])
                
                # Build redirect map: original → resolved
                redirect_map = {r["from"]: r["to"] for r in redirects}
                
                # print("----- OUTPUT for batch query is : ", pages)
                
                # For each input title, decide which resolved title to look up
                for title in batch:
                    resolved_title = redirect_map.get(title, title)
                    
                    # Find page info by resolved title
                    page_info = next(
                        (p for p in pages.values() if p.get("title") == resolved_title), 
                        None
                    )
                    if not page_info:
                        continue
                    
                    qid = page_info.get("pageprops", {}).get("wikibase_item")
                    short_desc = page_info.get("pageprops", {}).get("wikibase-shortdesc")
                    redirect_title = redirect_map.get(title)  # only set if it was redirected
                    
                    if qid:
                        qid_mapping[title] = {
                            "qid": qid,
                            "shortDesc": short_desc,
                            "redirectTitle": redirect_title
                        }
                
                # Small delay between batches
                await asyncio.sleep(0.1)
            
            return qid_mapping
        
        except Exception as e:
            self.logger.error(f"Error getting QIDs in batch: {e}")
            return {}

    async def _get_page_images_optimized(self, api_client: APIClient, page_title: str) -> List[Dict]:
        """Get page images with concurrent processing"""
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'images',
                'imlimit': 'max'
            }
            
            data = await api_client.get_json(self.api_url, params=params)
            if not data or 'query' not in data:
                return []
            
            page_id = list(data['query']['pages'].keys())[0]
            images = data['query']['pages'][page_id].get('images', [])
            
            # Limit and process images concurrently
            image_titles = [img['title'] for img in images[:20]]  # Limit to 20 images
            
            if not image_titles:
                return []
            
            # Create tasks for concurrent image info fetching
            tasks = [self._get_image_info_async(api_client, title) for title in image_titles]
            image_details = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out failed requests
            valid_images = []
            for detail in image_details:
                if isinstance(detail, dict) and detail.get('title'):
                    valid_images.append(detail)
                elif isinstance(detail, Exception):
                    self.logger.warning(f"Image processing failed: {detail}")
            
            return valid_images
            
        except Exception as e:
            self.logger.error(f"Error getting images for {page_title}: {e}")
            return []
    
    async def _get_image_info_async(self, api_client: APIClient, image_title: str) -> Dict:
        """Get image information asynchronously"""
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'titles': image_title,
                'prop': 'imageinfo',
                'iiprop': 'url|size|mime|extmetadata'
            }
            
            data = await api_client.get_json(self.api_url, params=params)
            if not data or 'query' not in data:
                return {'title': image_title}
            
            page_id = list(data['query']['pages'].keys())[0]
            imageinfo = data['query']['pages'][page_id].get('imageinfo', [{}])[0]
            
            return {
                'title': image_title,
                'url': imageinfo.get('url', ''),
                'width': imageinfo.get('width', 0),
                'height': imageinfo.get('height', 0),
                'size': imageinfo.get('size', 0),
                'mime': imageinfo.get('mime', ''),
                'description': imageinfo.get('extmetadata', {}).get('ImageDescription', {}).get('value', '')
            }
            
        except Exception as e:
            self.logger.error(f"Error getting image info for {image_title}: {e}")
            return {'title': image_title, 'error': str(e)}
    
    def _extract_tables(self, html_content: str) -> List[Dict]:
        """Extract tables with improved filtering and error handling"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            tables = soup.find_all('table')
            
            extracted_tables = []
            skip_classes = ['navbox', 'sidebar', 'infobox', 'metadata', 'ambox']
            
            for i, table in enumerate(tables):
                try:
                    # Skip navigation and metadata tables
                    table_classes = table.get('class', [])
                    if any(cls in ' '.join(table_classes) for cls in skip_classes):
                        continue
                    
                    table_data = {
                        'table_id': i + 1,
                        'headers': [],
                        'rows': [],
                        'caption': ''
                    }
                    
                    # Get table caption
                    caption = table.find('caption')
                    if caption:
                        table_data['caption'] = caption.get_text().strip()
                    
                    # Get headers
                    headers = table.find_all('th')
                    table_data['headers'] = [self._clean_cell_text(header) for header in headers]
                    
                    # Get rows
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if cells:
                            row_data = [self._clean_cell_text(cell) for cell in cells]
                            if any(cell.strip() for cell in row_data):  # Skip empty rows
                                table_data['rows'].append(row_data)
                    
                    # Only add tables with meaningful content
                    if len(table_data['rows']) > 1 or len(table_data['headers']) > 1:
                        extracted_tables.append(table_data)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing table {i}: {e}")
                    continue
            
            #self.logger.info(f"Extracted {len(extracted_tables)} tables")
            return extracted_tables
            
        except Exception as e:
            self.logger.error(f"Error extracting tables: {e}")
            return []
    
    def _clean_cell_text(self, cell) -> str:
        """Clean and normalize cell text"""
        try:
            # Replace <br> with spaces
            for br in cell.find_all("br"):
                br.replace_with(" ")
            
            text = cell.get_text(" ", strip=True)
            # Remove excessive whitespace
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except Exception:
            return ""
    
    def _extract_infobox(self, html_content: str) -> Dict:
        """Extract infobox with improved text processing"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            infobox = soup.find('table', class_=re.compile(r'infobox'))
            
            if not infobox:
                return {}
            
            infobox_data = {}
            rows = infobox.find_all('tr')
            
            for row in rows:
                try:
                    header = row.find('th')
                    data = row.find('td')
                    
                    if header and data:
                        key = self._clean_cell_text(header)
                        if not key:
                            continue
                        
                        # Handle lists and line breaks
                        for br in data.find_all("br"):
                            br.replace_with("\n")
                        
                        if data.find_all("li"):
                            value = "\n".join(self._clean_cell_text(li) for li in data.find_all("li"))
                        else:
                            value = data.get_text("\n", strip=True)
                        
                        # Clean up the value
                        value = re.sub(r'\n+', '\n', value).strip()
                        if value:
                            infobox_data[key] = value
                            
                except Exception as e:
                    self.logger.warning(f"Error processing infobox row: {e}")
                    continue
            
            return infobox_data
            
        except Exception as e:
            self.logger.error(f"Error extracting infobox: {e}")
            return {}
    
    def _extract_references(self, html_content: str) -> List[str]:
        """Extract references with improved detection"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            references = set()
            
            # Find reference sections
            ref_selectors = [
                'div.reflist',
                'div.references',
                'ol.references',
                '.citation',
                '.cite'
            ]
            
            for selector in ref_selectors:
                elements = soup.select(selector)
                for element in elements:
                    # Extract URLs from links
                    links = element.find_all('a', href=True)
                    for link in links:
                        href = link['href']
                        if href.startswith('http') and len(href) < 500:
                            references.add(href)
                    
                    # Extract text citations
                    text = element.get_text().strip()
                    if text and len(text) < 200:
                        # Look for common citation patterns
                        if any(pattern in text.lower() for pattern in ['doi:', 'isbn', 'pmid', 'arxiv']):
                            references.add(text)
            
            return list(references)[:50]  # Limit references
            
        except Exception as e:
            self.logger.error(f"Error extracting references: {e}")
            return []
    
    async def _extract_chunks_optimized(self, html_content: str, page_title: str, 
                                    qid: str = None, type_: str = None,
                                    internal_links: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Extract content chunks with optimized processing"""
        try:
            soup = BeautifulSoup(html_content, "lxml")
            source_url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
            chunks = []
            paragraph_index = 0

            # Create link lookup for fast reference matching
            link_lookup = {}
            if internal_links:
                for link in internal_links:
                    if link.get('title'):
                        link_lookup[link['title']] = link
                    if link.get('link'):
                        link_lookup[link['link']] = link

            # Track section hierarchy
            section_stack = {i: None for i in range(2, 7)}
            
            parser_output = soup.find("div", {"class": "mw-parser-output"})
            if not parser_output:
                self.logger.warning("No parser output found")
                return []

            for element in parser_output.children:
                if not hasattr(element, 'name') or not element.name:
                    continue
                
                # Handle headings
                heading = None
                if element.name and re.match(r"h[2-6]", element.name):
                    heading = element
                elif element.name == "div":
                    inner_heading = element.find(re.compile(r"h[2-6]"))
                    if inner_heading:
                        heading = inner_heading

                if heading:
                    level = int(heading.name[1])
                    section_title = heading.get_text().strip()

                    # Update section hierarchy properly (don’t reset higher parents)
                    section_stack[level] = section_title
                    for deeper in range(level + 1, 7):
                        section_stack[deeper] = None

                    paragraph_index = 0
                    continue

                # Handle content elements
                if element.name in ["p", "ul", "ol"]:
                    try:
                        chunk_text = self._extract_element_text(element)
                        if not chunk_text or len(chunk_text) < 20:
                            continue

                        paragraph_index += 1

                        # Build section path
                        section_parts = [section_stack[i] for i in range(2, 7) if section_stack[i]]
                        current_section = " - ".join(section_parts) if section_parts else "Introduction"

                        # Extract references with spans
                        references = self._extract_chunk_references_with_spans(element, link_lookup)

                        # Create chunk(s) with size limit
                        if len(chunk_text) > self.config.max_chunk_length:
                            sentences = self._split_into_sentences(chunk_text)
                            current_chunk = ""
                            current_refs = []

                            char_offset = 0
                            for sentence in sentences:
                                sent_start = char_offset
                                sent_end = char_offset + len(sentence)
                                char_offset = sent_end + 1  # +1 for space/punct split

                                # Find refs inside this sentence
                                sent_refs = [ref for ref in references 
                                            if ref["start"] >= sent_start and ref["end"] <= sent_end]

                                if len(current_chunk + sentence) > self.config.max_chunk_length:
                                    if current_chunk:
                                        chunks.append(self._create_chunk(
                                            current_section, paragraph_index, page_title,
                                            current_chunk, qid, type_, source_url, current_refs
                                        ))
                                        paragraph_index += 1
                                    current_chunk = sentence
                                    current_refs = sent_refs
                                else:
                                    current_chunk += " " + sentence if current_chunk else sentence
                                    current_refs.extend(sent_refs)

                            if current_chunk:
                                chunks.append(self._create_chunk(
                                    current_section, paragraph_index, page_title,
                                    current_chunk, qid, type_, source_url, current_refs
                                ))
                        else:
                            # Single chunk
                            refs_for_chunk = [ref for ref in references]
                            chunks.append(self._create_chunk(
                                current_section, paragraph_index, page_title,
                                chunk_text, qid, type_, source_url, refs_for_chunk
                            ))
                            
                    except Exception as e:
                        self.logger.warning(f"Error processing content element: {e}")
                        continue

            #self.logger.info(f"Generated {len(chunks)} content chunks")
            return chunks

        except Exception as e:
            self.logger.error(f"Error extracting chunks: {e}")
            return []
    
    def _extract_element_text(self, element) -> str:
        """Extract clean text from HTML element"""
        try:
            if element.name == "p":
                return element.get_text().strip()
            else:  # ul, ol
                items = [li.get_text(" ", strip=True) for li in element.find_all("li")]
                return "\n".join(items).strip()
        except Exception:
            return ""
    
    def _extract_chunk_references_with_spans(self, element, link_lookup: Dict) -> List[Dict]:
        """Extract references from element links"""
        references = []
        try:
            full_text = element.get_text()
            for a in element.find_all("a", href=True):
                href = a['href']
                title = a.get('title')
                if not href.startswith("/wiki/"):
                    continue

                link_url = f"https://en.wikipedia.org{href}"
                ref = None
                if title and title in link_lookup:
                    ref = link_lookup[title]
                elif link_url in link_lookup:
                    ref = link_lookup[link_url]

                if ref:
                    match = re.search(re.escape(a.get_text()), full_text)
                    if match:
                        ref_copy = ref.copy()
                        ref_copy["start"] = match.start()
                        ref_copy["end"] = match.end()
                        references.append(ref_copy)
        except Exception as e:
            self.logger.warning(f"Error extracting references with spans: {e}")
        return references


    def _deduplicate_links_by_qid(self, links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate links by QID, keeping only the final (non-redirected) titles"""
        try:
            # Group links by QID
            qid_groups = {}
            links_without_qid = []
            
            for link in links:
                qid = link.get("qid")
                if qid:
                    if qid not in qid_groups:
                        qid_groups[qid] = []
                    qid_groups[qid].append(link)
                else:
                    # Keep links without QID as-is
                    links_without_qid.append(link)
            
            # For each QID group, select the best representative
            deduplicated = []
            for qid, group_links in qid_groups.items():
                if len(group_links) == 1:
                    # Only one link for this QID
                    deduplicated.append(group_links[0])
                else:
                    # Multiple links for same QID - choose the final one
                    final_link = self._select_final_link(group_links)
                    deduplicated.append(final_link)
            
            # Add back links without QID
            deduplicated.extend(links_without_qid)
            
            self.logger.debug(f"Deduplicated {len(links)} links to {len(deduplicated)} links")
            return deduplicated
            
        except Exception as e:
            self.logger.error(f"Error deduplicating links: {e}")
            return links

    def _select_final_link(self, group_links: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the final (non-redirected) link from a group of links with same QID"""
        try:
            # Prefer links without redirectTitle (these are the final titles)
            non_redirected = [link for link in group_links if not link.get("redirectTitle")]
            
            if non_redirected:
                # If multiple non-redirected links, prefer the one with longer/more complete title
                return max(non_redirected, key=lambda x: len(x.get("title", "")))
            else:
                # If all are redirected, pick the one with the longest redirectTitle
                # (this shouldn't normally happen, but just in case)
                return max(group_links, key=lambda x: len(x.get("redirectTitle", "")))
                
        except Exception as e:
            self.logger.error(f"Error selecting final link: {e}")
            return group_links[0]  # Fallback to first link

    def _split_into_sentences(self, text: str) -> List[str]:
        """Improved sentence splitting"""
        try:
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
            return [s.strip() for s in sentences if s.strip()]
        except Exception:
            return [text]
    def _create_chunk(self, section: str, paragraph: int, title: str, 
                     text: str, qid: str, type_: str, source_url: str, 
                     references: List[Dict]) -> Dict:
        """Create a standardized chunk object"""
        return {
            "section": section,
            "paragraph": paragraph,
            "title": title,
            "chunk_text": text,
            "metadata": {
                "qid": qid,
                "type": type_,
                "source_url": source_url
            },
            "references": references
        }
    
    def save_to_json(self, data: Dict, filename: str):
        """Save data to JSON with error handling"""
        try:
            filepath = Path(filename)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            #self.logger.info(f"Data saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving to JSON {filename}: {e}")
            raise
    
    def save_tables_to_csv(self, tables: List[Dict], prefix: str):
        """Save tables to CSV with error handling"""
        try:
            for i, table in enumerate(tables):
                filename = f"{prefix}_table_{i+1}.csv"
                
                try:
                    if table['headers'] and table['rows']:
                        df = pd.DataFrame(table['rows'], columns=table['headers'])
                    elif table['rows']:
                        df = pd.DataFrame(table['rows'])
                    else:
                        self.logger.warning(f"Skipping empty table {i+1}")
                        continue
                    
                    df.to_csv(filename, index=False, encoding='utf-8')
                    #self.logger.info(f"Table {i+1} saved to {filename}")
                    
                except Exception as e:
                    self.logger.error(f"Error saving table {i+1}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error in save_tables_to_csv: {e}")

def setup_progress_tracking():
    """Setup progress tracking for long operations"""
    try:
        from tqdm import tqdm
        return tqdm
    except ImportError:
        # Fallback progress tracker
        class SimpleProgress:
            def __init__(self, total=None, desc=None):
                self.total = total
                self.desc = desc
                self.current = 0
            
            def update(self, n=1):
                self.current += n
                if self.total:
                    print(f"\r{self.desc}: {self.current}/{self.total}", end="", flush=True)
                else:
                    print(f"\r{self.desc}: {self.current}", end="", flush=True)
            
            def close(self):
                print()  # New line
        
        return SimpleProgress

async def extract_wikipedia_page_optimized(page_title: str, 
                                         config: ExtractionConfig = None,
                                         output_format: str = 'both',
                                         output_prefix: str = None,
                                         cache_dir: str = "./cache",
                                         log_level: str = "INFO",
                                         log_file: str = None) -> Dict[str, Any]:
    """
    Optimized Wikipedia page extraction with full error handling
    
    Args:
        page_title: Wikipedia page title to extract
        config: Extraction configuration
        output_format: 'json', 'csv', or 'both'  
        output_prefix: Output filename prefix
        cache_dir: Cache directory path
        log_level: Logging level
        log_file: Log file path
    
    Returns:
        Extracted data dictionary
    """
    # Setup logging
    logger = setup_logging(log_level, log_file)
    
    try:
        logger.info(f"Starting optimized extraction for: {page_title}")
        
        # Initialize extractor
        extractor_config = config or ExtractionConfig()
        extractor = OptimizedWikipediaExtractor(extractor_config, cache_dir)
        
        # Clear expired cache
        if extractor.cache:
            cleared = extractor.cache.clear_expired()
            if cleared > 0:
                logger.info(f"Cleared {cleared} expired cache entries")
        
        # Extract data
        data = await extractor.extract_page_data(page_title)
        
        # Determine output files
        output_prefix = output_prefix or page_title.replace(' ', '_').replace('/', '_')
        
        # Save data
        if output_format in ['json', 'both']:
            try:
                json_file = f"{output_prefix}_data.json"
                # extractor.save_to_json(data, json_file)
            except Exception as e:
                logger.error(f"Failed to save JSON: {e}")
        
        # if output_format in ['csv', 'both'] and data.get('tables'):
            # try:
                # extractor.save_tables_to_csv(data['tables'], output_prefix)
            # except Exception as e:
                # logger.error(f"Failed to save CSV tables: {e}")
        
        logger.info("Extraction completed successfully")
        return data
        
    except Exception as e:
        logger.error(f"Fatal error in extraction: {e}")
        raise

