"""
Excel Export Helpers for Wikidata Structured Data

Helper functions for extracting and formatting structured Wikidata properties
for Excel export.

Implements Phase 3, Step 9: Excel Export Logic.

Usage:
    from wikidata.excel_helpers import get_person_excel_columns, extract_person_data

    # Get column definitions
    columns = get_person_excel_columns()

    # Extract data for Excel row
    row_data = extract_person_data(structured_data)
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# GENERIC EXTRACTION HELPERS
# ============================================================================

def extract_simple_value(structured_data: Dict, property_id: str) -> str:
    """
    Extract simple value (dates, strings) from structured data.

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
            # Time value
            if 'value' in value:
                return str(value['value'])
            # Wikibase item
            elif 'name' in value:
                return str(value['name'])
            # Quantity
            elif 'amount' in value:
                unit = value.get('unit_label', '')
                return f"{value['amount']} {unit}".strip()
            # Coordinate
            elif 'latitude' in value and 'longitude' in value:
                return f"{value['latitude']}, {value['longitude']}"

        elif isinstance(value, list):
            # Array - return comma-separated names
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


def extract_entity_qid(structured_data: Dict, property_id: str) -> str:
    """
    Extract entity QID from wikibase-item.

    Args:
        structured_data: Structured key data dictionary
        property_id: Property ID to extract

    Returns:
        Entity QID or empty string
    """
    if property_id not in structured_data:
        return ''

    try:
        value = structured_data[property_id].get('value', {})

        if isinstance(value, dict):
            return value.get('qid', '')
        elif isinstance(value, list) and len(value) > 0:
            first = value[0]
            if isinstance(first, dict):
                return first.get('qid', '')

        return ''

    except Exception as e:
        logger.error(f"Error extracting entity QID for {property_id}: {e}")
        return ''


def count_array_values(structured_data: Dict, property_id: str) -> int:
    """
    Count items in array.

    Args:
        structured_data: Structured key data dictionary
        property_id: Property ID to count

    Returns:
        Count of array items or 0
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


def extract_array_names(structured_data: Dict, property_id: str) -> str:
    """
    Extract comma-separated names from array of entities.

    Args:
        structured_data: Structured key data dictionary
        property_id: Property ID to extract

    Returns:
        Comma-separated names or empty string
    """
    if property_id not in structured_data:
        return ''

    try:
        value = structured_data[property_id].get('value', [])

        if isinstance(value, list):
            names = []
            for item in value:
                if isinstance(item, dict):
                    name = item.get('name', '')
                    if name:
                        names.append(name)
            return ', '.join(names)

        return ''

    except Exception as e:
        logger.error(f"Error extracting array names for {property_id}: {e}")
        return ''


def extract_coordinates(structured_data: Dict, property_id: str = 'P625') -> str:
    """
    Extract coordinates as string.

    Args:
        structured_data: Structured key data dictionary
        property_id: Property ID (usually P625)

    Returns:
        Coordinates as "lat, lon" or empty string
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


# ============================================================================
# ENTITY-TYPE SPECIFIC COLUMN DEFINITIONS
# ============================================================================

def get_person_excel_columns() -> List[str]:
    """
    Get Excel column names for person entities.

    Returns:
        List of column names
    """
    return [
        'birth_date',
        'death_date',
        'birth_place',
        'death_place',
        'father_name',
        'mother_name',
        'spouse_names',
        'spouse_count',
        'children_count',
        'occupations',
        'positions_held'
    ]


def get_event_excel_columns() -> List[str]:
    """
    Get Excel column names for event entities.

    Returns:
        List of column names
    """
    return [
        'start_date',
        'end_date',
        'location',
        'participant_count',
        'participants',
        'casualties'
    ]


def get_location_excel_columns() -> List[str]:
    """
    Get Excel column names for location entities.

    Returns:
        List of column names
    """
    return [
        'coordinates',
        'population',
        'area',
        'parent_location',
        'country'
    ]


def get_dynasty_excel_columns() -> List[str]:
    """
    Get Excel column names for dynasty entities.

    Returns:
        List of column names
    """
    return [
        'inception_date',
        'dissolved_date',
        'founded_by',
        'members_count',
        'jurisdiction'
    ]


def get_political_entity_excel_columns() -> List[str]:
    """
    Get Excel column names for political entity entities.

    Returns:
        List of column names
    """
    return [
        'inception_date',
        'dissolved_date',
        'capital',
        'head_of_state',
        'head_of_government'
    ]


# ============================================================================
# ENTITY-TYPE SPECIFIC DATA EXTRACTION
# ============================================================================

def extract_person_data(structured_data: Dict) -> Dict[str, Any]:
    """
    Extract person-specific data for Excel export.

    Args:
        structured_data: Structured key data dictionary

    Returns:
        Dictionary with Excel column values
    """
    return {
        'birth_date': extract_simple_value(structured_data, 'P569'),
        'death_date': extract_simple_value(structured_data, 'P570'),
        'birth_place': extract_entity_name(structured_data, 'P19'),
        'death_place': extract_entity_name(structured_data, 'P20'),
        'father_name': extract_entity_name(structured_data, 'P22'),
        'mother_name': extract_entity_name(structured_data, 'P25'),
        'spouse_names': extract_array_names(structured_data, 'P26'),
        'spouse_count': count_array_values(structured_data, 'P26'),
        'children_count': count_array_values(structured_data, 'P40'),
        'occupations': extract_array_names(structured_data, 'P106'),
        'positions_held': extract_array_names(structured_data, 'P39')
    }


def extract_event_data(structured_data: Dict) -> Dict[str, Any]:
    """
    Extract event-specific data for Excel export.

    Args:
        structured_data: Structured key data dictionary

    Returns:
        Dictionary with Excel column values
    """
    return {
        'start_date': extract_simple_value(structured_data, 'P580'),
        'end_date': extract_simple_value(structured_data, 'P582'),
        'location': extract_entity_name(structured_data, 'P276'),
        'participant_count': count_array_values(structured_data, 'P710'),
        'participants': extract_array_names(structured_data, 'P710'),
        'casualties': extract_simple_value(structured_data, 'P1120')
    }


def extract_location_data(structured_data: Dict) -> Dict[str, Any]:
    """
    Extract location-specific data for Excel export.

    Args:
        structured_data: Structured key data dictionary

    Returns:
        Dictionary with Excel column values
    """
    return {
        'coordinates': extract_coordinates(structured_data, 'P625'),
        'population': extract_simple_value(structured_data, 'P1082'),
        'area': extract_simple_value(structured_data, 'P2046'),
        'parent_location': extract_entity_name(structured_data, 'P131'),
        'country': extract_entity_name(structured_data, 'P17')
    }


def extract_dynasty_data(structured_data: Dict) -> Dict[str, Any]:
    """
    Extract dynasty-specific data for Excel export.

    Args:
        structured_data: Structured key data dictionary

    Returns:
        Dictionary with Excel column values
    """
    return {
        'inception_date': extract_simple_value(structured_data, 'P571'),
        'dissolved_date': extract_simple_value(structured_data, 'P576'),
        'founded_by': extract_entity_name(structured_data, 'P112'),
        'members_count': count_array_values(structured_data, 'P527'),
        'jurisdiction': extract_entity_name(structured_data, 'P1001')
    }


def extract_political_entity_data(structured_data: Dict) -> Dict[str, Any]:
    """
    Extract political entity-specific data for Excel export.

    Args:
        structured_data: Structured key data dictionary

    Returns:
        Dictionary with Excel column values
    """
    return {
        'inception_date': extract_simple_value(structured_data, 'P571'),
        'dissolved_date': extract_simple_value(structured_data, 'P576'),
        'capital': extract_entity_name(structured_data, 'P36'),
        'head_of_state': extract_array_names(structured_data, 'P35'),
        'head_of_government': extract_array_names(structured_data, 'P6')
    }


# ============================================================================
# UNIFIED EXTRACTION FUNCTION
# ============================================================================

def extract_structured_data_for_excel(
    structured_data: Dict,
    entity_type: str
) -> Dict[str, Any]:
    """
    Extract structured data for Excel export based on entity type.

    Args:
        structured_data: Structured key data dictionary
        entity_type: Standard entity type (person, location, event, etc.)

    Returns:
        Dictionary with Excel column values

    Example:
        >>> data = extract_structured_data_for_excel(structured_data, 'person')
        >>> data['birth_date']
        '1869-10-02'
    """
    if entity_type == 'person':
        return extract_person_data(structured_data)
    elif entity_type == 'event':
        return extract_event_data(structured_data)
    elif entity_type == 'location':
        return extract_location_data(structured_data)
    elif entity_type == 'dynasty':
        return extract_dynasty_data(structured_data)
    elif entity_type == 'political_entity':
        return extract_political_entity_data(structured_data)
    else:
        # Return empty dict for unknown types
        return {}


def get_excel_columns_for_type(entity_type: str) -> List[str]:
    """
    Get Excel column names for entity type.

    Args:
        entity_type: Standard entity type

    Returns:
        List of column names
    """
    if entity_type == 'person':
        return get_person_excel_columns()
    elif entity_type == 'event':
        return get_event_excel_columns()
    elif entity_type == 'location':
        return get_location_excel_columns()
    elif entity_type == 'dynasty':
        return get_dynasty_excel_columns()
    elif entity_type == 'political_entity':
        return get_political_entity_excel_columns()
    else:
        return []


# ============================================================================
# COMMON METADATA EXTRACTION
# ============================================================================

def extract_common_metadata(enriched_data: Dict) -> Dict[str, Any]:
    """
    Extract common metadata for all entity types.

    Args:
        enriched_data: Complete enriched entity data

    Returns:
        Dictionary with common metadata
    """
    metadata = enriched_data.get('extraction_metadata', {})
    relationship_metadata = metadata.get('relationship_metadata', {})

    return {
        'has_structured_data': enriched_data.get('structured_key_data_extracted', False),
        'num_structured_properties': len(enriched_data.get('structured_key_data', {})),
        'entity_type_standardized': metadata.get('entity_type_standardized', ''),
        'wikidata_fetch_time': metadata.get('wikidata_fetch_time', 0),
        'family_connections': relationship_metadata.get('family_connections', 0),
        'political_connections': relationship_metadata.get('political_connections', 0),
        'geographic_connections': relationship_metadata.get('geographic_connections', 0),
        'total_entity_references': relationship_metadata.get('total_unique_entities_referenced', 0)
    }
