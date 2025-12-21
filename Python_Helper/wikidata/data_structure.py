"""
Data Structure Helpers

Helper functions for creating and validating structured_key_data format.
Implements the enhanced data structure design from Phase 2, Step 5.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def create_structured_data_entry(
    property_id: str,
    label: str,
    value: Any,
    value_type: str
) -> Dict:
    """
    Create standardized structured data entry.

    Args:
        property_id: Wikidata property ID (e.g., 'P569')
        label: Human-readable label (e.g., 'date_of_birth')
        value: Parsed value (dict, list, string, etc.)
        value_type: Type of value (time, wikibase-item, array, etc.)

    Returns:
        Standardized entry dictionary

    Example:
        >>> entry = create_structured_data_entry(
        ...     'P569',
        ...     'date_of_birth',
        ...     {'value': '1869-10-02', 'precision': 11, 'calendar': 'gregorian'},
        ...     'time'
        ... )
        >>> entry['label']
        'date_of_birth'
    """
    return {
        'label': label,
        'value': value,
        'value_type': value_type
    }


def validate_structured_data(data: Dict) -> bool:
    """
    Validate structured_key_data format.

    Args:
        data: Dictionary to validate

    Returns:
        True if valid, False otherwise

    Example:
        >>> data = {'P569': {'label': 'date_of_birth', 'value': {...}, 'value_type': 'time'}}
        >>> validate_structured_data(data)
        True
    """
    if not isinstance(data, dict):
        logger.error("Structured data must be a dictionary")
        return False

    for property_id, entry in data.items():
        # Validate property ID format
        if not property_id.startswith('P'):
            logger.error(f"Invalid property ID format: {property_id}")
            return False

        # Validate entry structure
        if not isinstance(entry, dict):
            logger.error(f"Entry for {property_id} must be a dictionary")
            return False

        # Check required fields
        required_fields = ['label', 'value', 'value_type']
        for field in required_fields:
            if field not in entry:
                logger.error(f"Entry for {property_id} missing required field: {field}")
                return False

        # Validate value based on type
        if not _validate_value_by_type(entry['value'], entry['value_type']):
            logger.error(f"Invalid value for {property_id} with type {entry['value_type']}")
            return False

    return True


def _validate_value_by_type(value: Any, value_type: str) -> bool:
    """
    Validate value matches expected type.

    Args:
        value: Value to validate
        value_type: Expected type

    Returns:
        True if valid, False otherwise
    """
    if value_type == 'time':
        return _validate_time_value(value)
    elif value_type == 'wikibase-item':
        return _validate_wikibase_item(value)
    elif value_type == 'quantity':
        return _validate_quantity(value)
    elif value_type == 'coordinate':
        return _validate_coordinate(value)
    elif value_type == 'array':
        return isinstance(value, list)
    elif value_type == 'array_with_qualifiers':
        return _validate_array_with_qualifiers(value)
    elif value_type == 'string':
        return isinstance(value, (str, int, float))
    else:
        logger.warning(f"Unknown value type: {value_type}")
        return True  # Allow unknown types


def _validate_time_value(value: Any) -> bool:
    """Validate time value structure."""
    if not isinstance(value, dict):
        return False

    required_fields = ['value', 'precision', 'calendar']
    return all(field in value for field in required_fields)


def _validate_wikibase_item(value: Any) -> bool:
    """Validate wikibase-item structure."""
    if not isinstance(value, dict):
        return False

    required_fields = ['qid']
    return all(field in value for field in required_fields)


def _validate_quantity(value: Any) -> bool:
    """Validate quantity structure."""
    if not isinstance(value, dict):
        return False

    required_fields = ['amount']
    return all(field in value for field in required_fields)


def _validate_coordinate(value: Any) -> bool:
    """Validate coordinate structure."""
    if not isinstance(value, dict):
        return False

    required_fields = ['latitude', 'longitude']
    return all(field in value for field in required_fields)


def _validate_array_with_qualifiers(value: Any) -> bool:
    """Validate array with qualifiers structure."""
    if not isinstance(value, list):
        return False

    # Check that at least one item has qualifiers
    for item in value:
        if isinstance(item, dict) and ('start_time' in item or 'end_time' in item):
            return True

    return False


def create_enriched_entity_structure(
    wikipedia_data: Dict,
    structured_key_data: Dict,
    extraction_success: bool,
    metadata: Optional[Dict] = None
) -> Dict:
    """
    Create complete enriched entity structure.

    Args:
        wikipedia_data: Original Wikipedia extraction data
        structured_key_data: Parsed Wikidata structured data
        extraction_success: Whether Wikidata extraction succeeded
        metadata: Additional metadata (fetch time, cache hits, etc.)

    Returns:
        Complete enriched entity dictionary

    Example:
        >>> result = create_enriched_entity_structure(
        ...     wikipedia_data={'title': 'Gandhi', 'qid': 'Q1001'},
        ...     structured_key_data={'P569': {...}},
        ...     extraction_success=True,
        ...     metadata={'wikidata_fetch_time': 1.23, 'cache_hits': 2}
        ... )
        >>> result['structured_key_data_extracted']
        True
    """
    # Start with Wikipedia data
    enriched = wikipedia_data.copy()

    # Add structured data
    enriched['structured_key_data'] = structured_key_data
    enriched['structured_key_data_extracted'] = extraction_success

    # Add/update extraction metadata
    if 'extraction_metadata' not in enriched:
        enriched['extraction_metadata'] = {}

    if metadata:
        enriched['extraction_metadata'].update(metadata)

    # Add timestamp if not present
    if 'timestamp' not in enriched['extraction_metadata']:
        enriched['extraction_metadata']['timestamp'] = datetime.now().isoformat()

    return enriched


def extract_simple_value(structured_data: Dict, property_id: str) -> str:
    """
    Extract simple value (dates, strings) from structured data.

    Used for Excel export and simple queries.

    Args:
        structured_data: Structured key data dictionary
        property_id: Property ID to extract (e.g., 'P569')

    Returns:
        Simple string value or empty string

    Example:
        >>> data = {'P569': {'value': {'value': '1869-10-02', ...}, ...}}
        >>> extract_simple_value(data, 'P569')
        '1869-10-02'
    """
    if property_id not in structured_data:
        return ''

    try:
        value = structured_data[property_id].get('value')

        if isinstance(value, dict):
            # Time value or coordinate
            if 'value' in value:
                return str(value['value'])
            # Wikibase item
            elif 'name' in value:
                return str(value['name'])
            # Quantity
            elif 'amount' in value:
                return str(value['amount'])
            # Coordinate
            elif 'latitude' in value and 'longitude' in value:
                return f"{value['latitude']}, {value['longitude']}"

        elif isinstance(value, list):
            # Array - return comma-separated
            simple_values = []
            for item in value:
                if isinstance(item, dict):
                    if 'name' in item:
                        simple_values.append(item['name'])
                    elif 'value' in item:
                        simple_values.append(str(item['value']))
                else:
                    simple_values.append(str(item))
            return ', '.join(simple_values)

        else:
            return str(value)

    except Exception as e:
        logger.error(f"Error extracting value for {property_id}: {e}")
        return ''


def extract_entity_name(structured_data: Dict, property_id: str) -> str:
    """
    Extract entity name from wikibase-item.

    Args:
        structured_data: Structured key data dictionary
        property_id: Property ID to extract

    Returns:
        Entity name or empty string

    Example:
        >>> data = {'P22': {'value': {'qid': 'Q123', 'name': 'John Doe'}, ...}}
        >>> extract_entity_name(data, 'P22')
        'John Doe'
    """
    if property_id not in structured_data:
        return ''

    try:
        value = structured_data[property_id].get('value', {})

        if isinstance(value, dict):
            return value.get('name', '')
        elif isinstance(value, list) and len(value) > 0:
            # Return first entity name
            first = value[0]
            if isinstance(first, dict):
                return first.get('name', '')

        return ''

    except Exception as e:
        logger.error(f"Error extracting entity name for {property_id}: {e}")
        return ''


def count_array_values(structured_data: Dict, property_id: str) -> int:
    """
    Count items in array.

    Args:
        structured_data: Structured key data dictionary
        property_id: Property ID to count

    Returns:
        Count of array items or 0

    Example:
        >>> data = {'P26': {'value': [{'name': 'A'}, {'name': 'B'}], ...}}
        >>> count_array_values(data, 'P26')
        2
    """
    if property_id not in structured_data:
        return 0

    try:
        value = structured_data[property_id].get('value', [])

        if isinstance(value, list):
            return len(value)

        return 0

    except Exception as e:
        logger.error(f"Error counting array for {property_id}: {e}")
        return 0


def extract_coordinates(structured_data: Dict, property_id: str) -> str:
    """
    Extract coordinates as string.

    Args:
        structured_data: Structured key data dictionary
        property_id: Property ID (usually P625)

    Returns:
        Coordinates as "lat, lon" or empty string

    Example:
        >>> data = {'P625': {'value': {'latitude': 28.6, 'longitude': 77.2}, ...}}
        >>> extract_coordinates(data, 'P625')
        '28.6, 77.2'
    """
    if property_id not in structured_data:
        return ''

    try:
        value = structured_data[property_id].get('value', {})

        if isinstance(value, dict):
            lat = value.get('latitude')
            lon = value.get('longitude')

            if lat is not None and lon is not None:
                return f"{lat}, {lon}"

        return ''

    except Exception as e:
        logger.error(f"Error extracting coordinates for {property_id}: {e}")
        return ''


def extract_quantity(structured_data: Dict, property_id: str) -> str:
    """
    Extract quantity with unit.

    Args:
        structured_data: Structured key data dictionary
        property_id: Property ID

    Returns:
        Quantity with unit as string or empty string

    Example:
        >>> data = {'P1082': {'value': {'amount': '1000000', 'unit_label': 'person'}, ...}}
        >>> extract_quantity(data, 'P1082')
        '1000000 person'
    """
    if property_id not in structured_data:
        return ''

    try:
        value = structured_data[property_id].get('value', {})

        if isinstance(value, dict):
            amount = value.get('amount')
            unit = value.get('unit_label', '')

            if amount:
                return f"{amount} {unit}".strip()

        return ''

    except Exception as e:
        logger.error(f"Error extracting quantity for {property_id}: {e}")
        return ''


def get_relationship_metadata(structured_data: Dict) -> Dict:
    """
    Calculate relationship metadata from structured data.

    Args:
        structured_data: Structured key data dictionary

    Returns:
        Dictionary with relationship counts

    Example:
        >>> metadata = get_relationship_metadata(structured_data)
        >>> metadata['family_connections']
        5
    """
    metadata = {
        'family_connections': 0,
        'political_connections': 0,
        'geographic_connections': 0,
        'total_unique_entities_referenced': 0
    }

    try:
        unique_entities = set()

        # Family properties
        family_props = ['P22', 'P25', 'P26', 'P40']  # father, mother, spouse, children
        for prop in family_props:
            if prop in structured_data:
                value = structured_data[prop].get('value')
                if isinstance(value, dict) and 'qid' in value:
                    unique_entities.add(value['qid'])
                    metadata['family_connections'] += 1
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and 'qid' in item:
                            unique_entities.add(item['qid'])
                            metadata['family_connections'] += 1

        # Political properties
        political_props = ['P39', 'P106']  # position_held, occupation
        for prop in political_props:
            if prop in structured_data:
                value = structured_data[prop].get('value')
                if isinstance(value, list):
                    metadata['political_connections'] += len(value)

        # Geographic properties
        geo_props = ['P19', 'P20', 'P27', 'P131']  # birth place, death place, country, location
        for prop in geo_props:
            if prop in structured_data:
                value = structured_data[prop].get('value')
                if isinstance(value, dict) and 'qid' in value:
                    unique_entities.add(value['qid'])
                    metadata['geographic_connections'] += 1

        metadata['total_unique_entities_referenced'] = len(unique_entities)

    except Exception as e:
        logger.error(f"Error calculating relationship metadata: {e}")

    return metadata
