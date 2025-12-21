"""
Wikidata Parser

Parses Wikidata JSON responses and transforms them to structured format.
Handles different value types (time, wikibase-item, quantity, coordinate, etc.).

Fully implemented in Phase 2 (Step 4).
Optimized in Phase 4 (Step 11) with selective property extraction and parallel processing.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class WikidataParser:
    """
    Parser for Wikidata JSON responses.

    Transforms raw Wikidata API responses into structured_key_data format
    based on property configurations.
    """

    def __init__(self, entity_cache=None, wikidata_client=None):
        """
        Initialize Wikidata parser.

        Args:
            entity_cache: EntityReferenceCache for resolving entity references
            wikidata_client: WikidataClient for fetching entity details (optional)
        """
        self.entity_cache = entity_cache
        self.wikidata_client = wikidata_client
        logger.info("WikidataParser initialized")

    def parse_entity(
        self,
        wikidata_json: Dict,
        property_config: List[Dict]
    ) -> Dict:
        """
        Parse Wikidata JSON to structured_key_data format.

        Optimized in Phase 4 Step 11 to only process configured properties,
        skipping unnecessary JSON traversal.

        Args:
            wikidata_json: Raw Wikidata API response
            property_config: List of properties to extract (from YAML config)

        Returns:
            Dictionary in structured_key_data format

        Example:
            >>> parser = WikidataParser(cache)
            >>> result = parser.parse_entity(wikidata_json, person_config)
            >>> result['P569']['label']
            'date_of_birth'
        """
        structured_data = {}

        try:
            # Extract entities from response
            entities = wikidata_json.get('entities', {})
            if not entities:
                logger.warning("No entities found in Wikidata response")
                return {}

            # Get first entity (should be the one we requested)
            entity_data = list(entities.values())[0]
            claims = entity_data.get('claims', {})

            # Create mapping of property IDs from config (Phase 4 Step 11 optimization)
            # Pre-build set for O(1) lookup
            property_map = {p['property_id']: p for p in property_config}
            property_ids_set = set(property_map.keys())

            # OPTIMIZATION: Only iterate over configured properties
            # Skip all other properties in claims to reduce processing time
            filtered_claims = {
                pid: claims[pid]
                for pid in property_ids_set
                if pid in claims
            }

            logger.debug(
                f"Filtering {len(claims)} total properties to {len(filtered_claims)} configured properties"
            )

            # Process each configured property
            for property_id, property_claims in filtered_claims.items():
                prop_config = property_map[property_id]

                # Parse based on value type and multi-value setting
                parsed_value = self._parse_property_claims(
                    property_claims,
                    prop_config
                )

                if parsed_value is not None:
                    structured_data[property_id] = {
                        'label': prop_config['label'],
                        'value': parsed_value,
                        'value_type': self._determine_value_type(
                            parsed_value,
                            prop_config.get('multi_value', False)
                        )
                    }

            logger.info(f"Successfully parsed {len(structured_data)} properties from Wikidata")
            return structured_data

        except Exception as e:
            logger.error(f"Error parsing Wikidata entity: {e}", exc_info=True)
            return {}

    def _parse_property_claims(
        self,
        claims: List[Dict],
        prop_config: Dict
    ) -> Any:
        """
        Parse all claims for a property.

        Args:
            claims: List of claim objects for this property
            prop_config: Property configuration from YAML

        Returns:
            Parsed value (single value or array)
        """
        # Filter claims by rank (prefer preferred, then normal, ignore deprecated)
        filtered_claims = self._filter_claims_by_rank(claims)

        if not filtered_claims:
            return None

        value_type = prop_config.get('value_type', 'string')
        multi_value = prop_config.get('multi_value', False)

        # Parse each claim
        parsed_values = []
        for claim in filtered_claims:
            parsed = self._parse_claim(claim, value_type, prop_config)
            if parsed is not None:
                parsed_values.append(parsed)

        if not parsed_values:
            return None

        # Return single value or array based on config
        if multi_value:
            return parsed_values
        else:
            # Return first value for single-value properties
            return parsed_values[0]

    def _filter_claims_by_rank(self, claims: List[Dict]) -> List[Dict]:
        """
        Filter claims by rank preference.

        Priority: preferred > normal > deprecated (excluded)
        """
        preferred = [c for c in claims if c.get('rank') == 'preferred']
        if preferred:
            return preferred

        normal = [c for c in claims if c.get('rank') == 'normal']
        return normal

    def _parse_claim(
        self,
        claim: Dict,
        value_type: str,
        prop_config: Dict
    ) -> Any:
        """
        Parse individual claim based on value type.

        Args:
            claim: Wikidata claim object
            value_type: Type of value (time, wikibase-item, quantity, etc.)
            prop_config: Property configuration

        Returns:
            Parsed value or None
        """
        try:
            # Extract mainsnak
            mainsnak = claim.get('mainsnak', {})

            # Check if value exists
            if mainsnak.get('snaktype') != 'value':
                return None

            datavalue = mainsnak.get('datavalue', {})
            value = datavalue.get('value')

            if value is None:
                return None

            # Parse based on value type
            if value_type == 'time':
                parsed = self._parse_time_value(value)
            elif value_type == 'wikibase-item':
                parsed = self._parse_wikibase_item(value, prop_config)
            elif value_type == 'quantity':
                parsed = self._parse_quantity(value)
            elif value_type == 'coordinate':
                parsed = self._parse_coordinate(value)
            elif value_type == 'string':
                parsed = value
            elif value_type == 'monolingualtext':
                parsed = value.get('text', '')
            elif value_type == 'url':
                parsed = value
            else:
                logger.warning(f"Unknown value type: {value_type}")
                parsed = str(value)

            # Handle qualifiers for position_held (P39) and similar properties
            if prop_config.get('property_id') == 'P39' and isinstance(parsed, dict):
                qualifiers = self._parse_qualifiers(claim.get('qualifiers', {}))
                if qualifiers:
                    parsed.update(qualifiers)

            return parsed

        except Exception as e:
            logger.error(f"Error parsing claim: {e}", exc_info=True)
            return None

    def _parse_time_value(self, time_data: Dict) -> Dict:
        """
        Parse time datatype with precision.

        Args:
            time_data: Wikidata time value object

        Returns:
            Standardized time dictionary

        Example:
            >>> result = parser._parse_time_value({
            ...     'time': '+1869-10-02T00:00:00Z',
            ...     'precision': 11,
            ...     'calendarmodel': 'http://www.wikidata.org/entity/Q1985727'
            ... })
            >>> result['value']
            '1869-10-02'
        """
        try:
            time_str = time_data.get('time', '')
            precision = time_data.get('precision', 11)
            calendar_uri = time_data.get('calendarmodel', '')

            # Extract calendar type from URI
            calendar = 'gregorian'
            if 'Q1985786' in calendar_uri:
                calendar = 'julian'

            # Parse time string (+YYYY-MM-DDTHH:MM:SSZ)
            # Remove leading + or -
            time_str = time_str.lstrip('+').lstrip('-')

            # Extract date based on precision
            # 11 = day, 10 = month, 9 = year, 8 = decade, etc.
            if precision >= 11:  # Day precision
                value = time_str[:10]  # YYYY-MM-DD
            elif precision == 10:  # Month precision
                value = time_str[:7]  # YYYY-MM
            elif precision >= 9:  # Year precision
                value = time_str[:4]  # YYYY
            else:
                value = time_str[:4]  # Default to year

            return {
                'value': value,
                'precision': precision,
                'calendar': calendar
            }

        except Exception as e:
            logger.error(f"Error parsing time value: {e}")
            return {
                'value': str(time_data),
                'precision': 9,
                'calendar': 'gregorian'
            }

    def _parse_wikibase_item(
        self,
        item_data: Dict,
        prop_config: Dict
    ) -> Dict:
        """
        Parse entity reference, fetch from cache or API if fetch_depth >= 1.

        Args:
            item_data: Wikidata item value object
            prop_config: Property configuration (includes fetch_depth)

        Returns:
            Entity reference dictionary

        Example:
            >>> result = parser._parse_wikibase_item(
            ...     {'id': 'Q5682621'},
            ...     {'fetch_depth': 1}
            ... )
            >>> result['qid']
            'Q5682621'
        """
        try:
            qid = item_data.get('id')
            if not qid:
                return None

            # Check if we should fetch entity details
            fetch_depth = prop_config.get('fetch_depth', 0)

            if fetch_depth >= 1:
                # Try to get from cache first
                if self.entity_cache:
                    cached = self.entity_cache.get(qid)
                    if cached:
                        logger.debug(f"Cache hit for entity reference {qid}")
                        return cached

                # Fetch from Wikidata API if we have a client
                if self.wikidata_client:
                    logger.debug(f"Fetching entity reference details for {qid}")
                    entity_json = self.wikidata_client.fetch_entity_data(qid)

                    if entity_json:
                        # Extract label, description, and instance_of (P31)
                        entities = entity_json.get('entities', {})
                        if qid in entities or len(entities) == 1:
                            entity_data = entities.get(qid, list(entities.values())[0])

                            # Get English label
                            labels = entity_data.get('labels', {})
                            name = labels.get('en', {}).get('value', qid)

                            # Get English description
                            descriptions = entity_data.get('descriptions', {})
                            description = descriptions.get('en', {}).get('value', '')

                            # Get instance_of (P31) for type
                            claims = entity_data.get('claims', {})
                            p31_claims = claims.get('P31', [])
                            entity_type = ''
                            entity_type_label = ''
                            if p31_claims:
                                # Get first instance_of
                                first_claim = p31_claims[0]
                                if first_claim.get('mainsnak', {}).get('snaktype') == 'value':
                                    type_qid = first_claim.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')
                                    if type_qid:
                                        entity_type = type_qid
                                        # Fetch type label from Wikidata
                                        entity_type_label = self._fetch_entity_label(type_qid)

                            result = {
                                'qid': qid,
                                'name': name,
                                'description': description
                            }

                            # Only include type fields if we have type information
                            if entity_type:
                                result['type'] = entity_type
                                result['type_label'] = entity_type_label if entity_type_label else entity_type

                            # Cache the result
                            if self.entity_cache:
                                self.entity_cache.add(qid, result)

                            return result

            # Return minimal reference if fetch_depth is 0 or fetching failed
            return {
                'qid': qid,
                'name': item_data.get('label', qid),
                'description': ''
                # type and type_label omitted if not available
            }

        except Exception as e:
            logger.error(f"Error parsing wikibase item: {e}")
            return None

    def _parse_quantity(self, quantity_data: Dict) -> Dict:
        """
        Parse quantity with units.

        Args:
            quantity_data: Wikidata quantity value object

        Returns:
            Quantity dictionary with amount and unit

        Example:
            >>> result = parser._parse_quantity({
            ...     'amount': '+350000',
            ...     'unit': 'http://www.wikidata.org/entity/Q11573'
            ... })
            >>> result['amount']
            '350000'
        """
        try:
            amount = quantity_data.get('amount', '0')
            unit_uri = quantity_data.get('unit', '1')

            # Remove leading +
            amount = amount.lstrip('+')

            # Extract unit QID from URI
            unit_qid = None
            unit_label = ''
            if 'entity/' in unit_uri:
                unit_qid = unit_uri.split('entity/')[-1]
                # Could fetch unit label from cache, but skip for now
                unit_label = unit_qid

            return {
                'amount': amount,
                'unit': unit_qid,
                'unit_label': unit_label
            }

        except Exception as e:
            logger.error(f"Error parsing quantity: {e}")
            return {
                'amount': str(quantity_data),
                'unit': None,
                'unit_label': ''
            }

    def _parse_coordinate(self, coord_data: Dict) -> Dict:
        """
        Parse geographic coordinates.

        Args:
            coord_data: Wikidata coordinate value object

        Returns:
            Coordinate dictionary

        Example:
            >>> result = parser._parse_coordinate({
            ...     'latitude': 28.6139,
            ...     'longitude': 77.2090,
            ...     'precision': 0.0001,
            ...     'globe': 'http://www.wikidata.org/entity/Q2'
            ... })
            >>> result['latitude']
            28.6139
        """
        try:
            latitude = coord_data.get('latitude', 0.0)
            longitude = coord_data.get('longitude', 0.0)
            precision = coord_data.get('precision', 0.0001)
            globe_uri = coord_data.get('globe', '')

            # Extract globe (usually Earth - Q2)
            globe = 'earth'
            if 'entity/' in globe_uri:
                globe_qid = globe_uri.split('entity/')[-1]
                if globe_qid != 'Q2':
                    globe = globe_qid

            return {
                'latitude': latitude,
                'longitude': longitude,
                'precision': precision,
                'globe': globe
            }

        except Exception as e:
            logger.error(f"Error parsing coordinate: {e}")
            return {
                'latitude': 0.0,
                'longitude': 0.0,
                'precision': 0.0001,
                'globe': 'earth'
            }

    def _parse_qualifiers(self, qualifiers: Dict) -> Dict:
        """
        Parse qualifiers for properties like position_held (P39).

        Args:
            qualifiers: Dictionary of qualifiers

        Returns:
            Dictionary with parsed qualifier values
        """
        result = {}

        try:
            # Parse start time (P580)
            if 'P580' in qualifiers:
                start_claim = qualifiers['P580'][0]
                if start_claim.get('snaktype') == 'value':
                    time_data = start_claim.get('datavalue', {}).get('value')
                    if time_data:
                        parsed_time = self._parse_time_value(time_data)
                        result['start_time'] = parsed_time['value']

            # Parse end time (P582)
            if 'P582' in qualifiers:
                end_claim = qualifiers['P582'][0]
                if end_claim.get('snaktype') == 'value':
                    time_data = end_claim.get('datavalue', {}).get('value')
                    if time_data:
                        parsed_time = self._parse_time_value(time_data)
                        result['end_time'] = parsed_time['value']

        except Exception as e:
            logger.error(f"Error parsing qualifiers: {e}")

        return result

    def _resolve_entity_references_parallel(
        self,
        entity_qids: List[str],
        wikidata_client=None,
        max_workers: int = 5
    ) -> Dict[str, Dict]:
        """
        Resolve multiple entity references in parallel.

        Phase 4 Step 11 optimization: Use ThreadPoolExecutor to fetch
        multiple entity references concurrently, reducing total fetch time.

        Args:
            entity_qids: List of QIDs to resolve
            wikidata_client: WikidataClient instance (optional, for batch fetching)
            max_workers: Maximum number of parallel workers

        Returns:
            Dictionary mapping QID to entity data

        Example:
            >>> qids = ['Q1001', 'Q1156', 'Q12345']
            >>> results = parser._resolve_entity_references_parallel(qids, client)
            >>> len(results)
            3
        """
        if not entity_qids:
            return {}

        results = {}

        # If we have a client, use batch fetching (most efficient)
        if wikidata_client and hasattr(wikidata_client, 'fetch_multiple_entities'):
            logger.debug(f"Batch fetching {len(entity_qids)} entity references")
            return wikidata_client.fetch_multiple_entities(entity_qids)

        # Otherwise, use parallel individual fetches
        logger.debug(f"Parallel fetching {len(entity_qids)} entity references")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all fetch tasks
            future_to_qid = {
                executor.submit(self._fetch_entity_reference, qid): qid
                for qid in entity_qids
            }

            # Collect results as they complete
            for future in as_completed(future_to_qid):
                qid = future_to_qid[future]
                try:
                    entity_data = future.result()
                    if entity_data:
                        results[qid] = entity_data
                except Exception as e:
                    logger.error(f"Error fetching entity reference {qid}: {e}")

        logger.info(f"Resolved {len(results)}/{len(entity_qids)} entity references in parallel")
        return results

    def _fetch_entity_reference(self, qid: str) -> Optional[Dict]:
        """
        Fetch minimal entity reference data (helper for parallel processing).

        Args:
            qid: Entity QID to fetch

        Returns:
            Minimal entity data or None
        """
        try:
            # Check cache first
            if self.entity_cache:
                cached = self.entity_cache.get(qid)
                if cached:
                    return cached

            # Return minimal placeholder (detailed fetching done by client/enricher)
            return {
                'qid': qid,
                'name': qid,
                'description': '',
                'type': ''
            }

        except Exception as e:
            logger.error(f"Error fetching reference for {qid}: {e}")
            return None

    def _fetch_entity_label(self, qid: str) -> str:
        """
        Fetch just the label for an entity (used for type labels).

        Args:
            qid: Entity QID

        Returns:
            English label or QID if not found
        """
        try:
            # Check cache first
            if self.entity_cache:
                cached = self.entity_cache.get(qid)
                if cached and cached.get('name'):
                    return cached['name']

            # Fetch from API if we have a client
            if self.wikidata_client:
                entity_json = self.wikidata_client.fetch_entity_data(qid)
                if entity_json:
                    entities = entity_json.get('entities', {})
                    if qid in entities or len(entities) == 1:
                        entity_data = entities.get(qid, list(entities.values())[0])
                        labels = entity_data.get('labels', {})
                        label = labels.get('en', {}).get('value', qid)
                        return label

            return qid

        except Exception as e:
            logger.error(f"Error fetching label for {qid}: {e}")
            return qid

    def _determine_value_type(self, value: Any, multi_value: bool) -> str:
        """
        Determine the value_type string for structured_key_data.

        Args:
            value: Parsed value
            multi_value: Whether property allows multiple values

        Returns:
            Value type string
        """
        if multi_value or isinstance(value, list):
            # Check if it has qualifiers (like position_held)
            if isinstance(value, list) and len(value) > 0:
                if isinstance(value[0], dict) and ('start_time' in value[0] or 'end_time' in value[0]):
                    return 'array_with_qualifiers'
            return 'array'

        if isinstance(value, dict):
            if 'latitude' in value and 'longitude' in value:
                return 'coordinate'
            elif 'amount' in value:
                return 'quantity'
            elif 'value' in value and 'precision' in value:
                return 'time'
            elif 'qid' in value:
                return 'wikibase-item'

        return 'string'
