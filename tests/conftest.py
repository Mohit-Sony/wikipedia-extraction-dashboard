"""Pytest configuration and shared fixtures for all tests."""

import pytest
import sys
from pathlib import Path

# Add Python_Helper to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "Python_Helper"))


@pytest.fixture
def sample_wikidata_person_response():
    """Sample Wikidata API response for a person (Gandhi Q1001)."""
    return {
        "entities": {
            "Q1001": {
                "type": "item",
                "id": "Q1001",
                "labels": {
                    "en": {"language": "en", "value": "Mahatma Gandhi"}
                },
                "descriptions": {
                    "en": {"language": "en", "value": "pre-eminent leader of Indian nationalism"}
                },
                "claims": {
                    "P31": [  # instance of
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "datatype": "wikibase-item",
                                "datavalue": {
                                    "value": {"id": "Q5", "entity-type": "item"},
                                    "type": "wikibase-entityid"
                                }
                            },
                            "rank": "normal"
                        }
                    ],
                    "P569": [  # date of birth
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "datatype": "time",
                                "datavalue": {
                                    "value": {
                                        "time": "+1869-10-02T00:00:00Z",
                                        "precision": 11,
                                        "calendarmodel": "http://www.wikidata.org/entity/Q1985727"
                                    },
                                    "type": "time"
                                }
                            },
                            "rank": "normal"
                        }
                    ],
                    "P570": [  # date of death
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "datatype": "time",
                                "datavalue": {
                                    "value": {
                                        "time": "+1948-01-30T00:00:00Z",
                                        "precision": 11,
                                        "calendarmodel": "http://www.wikidata.org/entity/Q1985727"
                                    },
                                    "type": "time"
                                }
                            },
                            "rank": "normal"
                        }
                    ],
                    "P22": [  # father
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "datatype": "wikibase-item",
                                "datavalue": {
                                    "value": {"id": "Q5682621", "entity-type": "item"},
                                    "type": "wikibase-entityid"
                                }
                            },
                            "rank": "normal"
                        }
                    ]
                }
            }
        }
    }


@pytest.fixture
def sample_wikidata_location_response():
    """Sample Wikidata API response for a location (Mumbai Q1156)."""
    return {
        "entities": {
            "Q1156": {
                "type": "item",
                "id": "Q1156",
                "labels": {
                    "en": {"language": "en", "value": "Mumbai"}
                },
                "descriptions": {
                    "en": {"language": "en", "value": "capital of Maharashtra, India"}
                },
                "claims": {
                    "P31": [  # instance of
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "datatype": "wikibase-item",
                                "datavalue": {
                                    "value": {"id": "Q515", "entity-type": "item"},
                                    "type": "wikibase-entityid"
                                }
                            },
                            "rank": "normal"
                        }
                    ],
                    "P625": [  # coordinate location
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "datatype": "globe-coordinate",
                                "datavalue": {
                                    "value": {
                                        "latitude": 19.0760,
                                        "longitude": 72.8777,
                                        "precision": 0.0001,
                                        "globe": "http://www.wikidata.org/entity/Q2"
                                    },
                                    "type": "globecoordinate"
                                }
                            },
                            "rank": "normal"
                        }
                    ],
                    "P1082": [  # population
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "datatype": "quantity",
                                "datavalue": {
                                    "value": {
                                        "amount": "+12442373",
                                        "unit": "1"
                                    },
                                    "type": "quantity"
                                }
                            },
                            "rank": "normal"
                        }
                    ]
                }
            }
        }
    }


@pytest.fixture
def sample_entity_reference():
    """Sample entity reference for cache."""
    return {
        "qid": "Q5682621",
        "name": "Karamchand Gandhi",
        "description": "father of Mahatma Gandhi",
        "type": "human"
    }
