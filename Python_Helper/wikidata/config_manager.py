"""
Property Configuration Manager

Manages loading and accessing Wikidata property configurations from YAML files.
Each entity type (person, event, location, dynasty, political_entity) has its own
configuration file defining which Wikidata properties to extract.
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PropertyConfigManager:
    """
    Manages property configuration files for different entity types.

    Loads YAML configuration files that define which Wikidata properties
    to extract for each entity type. Supports dynamic property addition
    and configuration reloading.
    """

    def __init__(self, config_dir: str = "config/properties"):
        """
        Initialize the PropertyConfigManager.

        Args:
            config_dir: Directory containing YAML configuration files
        """
        self.config_dir = Path(config_dir)
        self.configs: Dict[str, Dict] = {}
        self._load_all_configs()

    def _load_all_configs(self):
        """Load all YAML configuration files from the config directory."""
        if not self.config_dir.exists():
            logger.error(f"Configuration directory not found: {self.config_dir}")
            raise FileNotFoundError(f"Configuration directory not found: {self.config_dir}")

        # Load each YAML file
        for yaml_file in self.config_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    config = yaml.safe_load(f)

                entity_type = config.get('entity_type')
                if not entity_type:
                    logger.warning(f"No entity_type found in {yaml_file}, skipping")
                    continue

                self.configs[entity_type] = config
                logger.info(f"Loaded configuration for entity type: {entity_type}")

            except Exception as e:
                logger.error(f"Failed to load config from {yaml_file}: {e}")
                continue

        if not self.configs:
            logger.warning("No configuration files loaded successfully")

    def get_properties_for_type(self, entity_type: str) -> List[Dict]:
        """
        Get property configuration for a specific entity type.

        Args:
            entity_type: The type of entity (person, event, location, etc.)

        Returns:
            List of property configuration dictionaries

        Example:
            >>> manager = PropertyConfigManager()
            >>> props = manager.get_properties_for_type('person')
            >>> props[0]['property_id']
            'P569'
        """
        # Normalize entity type
        normalized_type = self._normalize_entity_type(entity_type)

        if normalized_type not in self.configs:
            logger.warning(f"No configuration found for entity type: {entity_type}, using 'other'")
            normalized_type = 'other'

        if normalized_type not in self.configs:
            logger.error(f"No configuration found for entity type: {normalized_type}")
            return []

        config = self.configs[normalized_type]
        return config.get('properties', [])

    def _normalize_entity_type(self, entity_type: str) -> str:
        """
        Normalize entity type to match configuration file names.

        Maps common variations to standard types:
        - human -> person
        - place -> location
        - etc.

        Args:
            entity_type: Raw entity type string

        Returns:
            Normalized entity type
        """
        type_mapping = {
            'human': 'person',
            'people': 'person',
            'place': 'location',
            'geographic location': 'location',
            'battle': 'event',
            'war': 'event',
            'kingdom': 'political_entity',
            'empire': 'political_entity',
            'sultanate': 'political_entity',
            'royal house': 'dynasty',
            'royal family': 'dynasty',
        }

        # Convert to lowercase for comparison
        normalized = entity_type.lower().strip()

        # Check direct mapping
        if normalized in type_mapping:
            return type_mapping[normalized]

        # Check if it's already a standard type
        if normalized in ['person', 'event', 'location', 'dynasty', 'political_entity', 'other']:
            return normalized

        # Default to 'other' for unknown types
        return 'other'

    def add_property_dynamically(self, entity_type: str, property_config: Dict):
        """
        Add a new property to entity type configuration at runtime.

        Args:
            entity_type: The entity type to add the property to
            property_config: Dictionary with property configuration
                           {
                               'property_id': 'P123',
                               'label': 'property_label',
                               'value_type': 'time',
                               'priority': 'high'
                           }

        Example:
            >>> manager = PropertyConfigManager()
            >>> manager.add_property_dynamically('person', {
            ...     'property_id': 'P123',
            ...     'label': 'new_property',
            ...     'value_type': 'string',
            ...     'priority': 'low'
            ... })
        """
        normalized_type = self._normalize_entity_type(entity_type)

        if normalized_type not in self.configs:
            logger.warning(f"Entity type {normalized_type} not found, creating new config")
            self.configs[normalized_type] = {
                'entity_type': normalized_type,
                'description': f'Dynamically created configuration for {normalized_type}',
                'properties': []
            }

        # Check if property already exists
        existing_props = self.configs[normalized_type].get('properties', [])
        property_id = property_config.get('property_id')

        if any(p.get('property_id') == property_id for p in existing_props):
            logger.warning(f"Property {property_id} already exists for {normalized_type}, skipping")
            return

        # Add property
        self.configs[normalized_type]['properties'].append(property_config)
        logger.info(f"Added property {property_id} to {normalized_type}")

    def reload_config(self, entity_type: str):
        """
        Reload configuration from disk for a specific entity type.

        Useful for hot-reloading configuration changes without restarting.

        Args:
            entity_type: The entity type to reload
        """
        normalized_type = self._normalize_entity_type(entity_type)
        config_file = self.config_dir / f"{normalized_type}.yaml"

        if not config_file.exists():
            logger.error(f"Configuration file not found: {config_file}")
            return

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                self.configs[normalized_type] = config
                logger.info(f"Reloaded configuration for {normalized_type}")
        except Exception as e:
            logger.error(f"Failed to reload configuration for {normalized_type}: {e}")

    def get_all_entity_types(self) -> List[str]:
        """
        Get list of all configured entity types.

        Returns:
            List of entity type names
        """
        return list(self.configs.keys())

    def validate_config(self, entity_type: str) -> bool:
        """
        Validate configuration for an entity type.

        Checks that required fields are present and properly formatted.

        Args:
            entity_type: The entity type to validate

        Returns:
            True if configuration is valid, False otherwise
        """
        normalized_type = self._normalize_entity_type(entity_type)

        if normalized_type not in self.configs:
            logger.error(f"No configuration found for {normalized_type}")
            return False

        config = self.configs[normalized_type]

        # Check required fields
        if 'entity_type' not in config:
            logger.error(f"Missing 'entity_type' in configuration for {normalized_type}")
            return False

        if 'properties' not in config:
            logger.error(f"Missing 'properties' in configuration for {normalized_type}")
            return False

        # Validate each property
        for prop in config['properties']:
            if 'property_id' not in prop:
                logger.error(f"Missing 'property_id' in property for {normalized_type}")
                return False

            if 'label' not in prop:
                logger.error(f"Missing 'label' in property {prop.get('property_id')} for {normalized_type}")
                return False

            if 'value_type' not in prop:
                logger.error(f"Missing 'value_type' in property {prop.get('property_id')} for {normalized_type}")
                return False

        logger.info(f"Configuration for {normalized_type} is valid")
        return True
