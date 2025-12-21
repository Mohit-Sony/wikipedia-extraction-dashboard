import requests
from bs4 import BeautifulSoup
import json
import time

def scrape_wikidata_properties():
    url = "https://www.wikidata.org/wiki/Wikidata:Database_reports/List_of_properties/all"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print("Fetching page...")
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    print("Parsing HTML...")
    soup = BeautifulSoup(response.content, 'html.parser')

    properties = []

    # Find the main table containing properties
    tables = soup.find_all('table', class_='wikitable')

    if not tables:
        print("No tables found. Looking for alternative structure...")
        tables = soup.find_all('table')

    print(f"Found {len(tables)} table(s)")

    for table in tables:
        rows = table.find_all('tr')

        # Skip header row
        for row in rows[1:]:
            cols = row.find_all(['td', 'th'])

            if len(cols) >= 3:
                property_data = {}

                # Extract property ID
                prop_id_cell = cols[0]
                prop_id_link = prop_id_cell.find('a')
                if prop_id_link:
                    property_data['id'] = prop_id_link.text.strip()
                    property_data['url'] = 'https://www.wikidata.org' + prop_id_link.get('href', '')
                else:
                    property_data['id'] = prop_id_cell.text.strip()

                # Extract label/name
                if len(cols) > 1:
                    property_data['label'] = cols[1].text.strip()

                # Extract description
                if len(cols) > 2:
                    property_data['description'] = cols[2].text.strip()

                # Extract datatype if available
                if len(cols) > 3:
                    property_data['datatype'] = cols[3].text.strip()

                # Only add if we have at least an ID
                if property_data.get('id') and property_data['id'].startswith('P'):
                    properties.append(property_data)

    print(f"Extracted {len(properties)} properties")

    # Save to JSON
    output_file = 'wikidata_properties.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(properties, f, indent=2, ensure_ascii=False)

    print(f"Saved to {output_file}")

    return properties

if __name__ == "__main__":
    properties = scrape_wikidata_properties()
    print(f"\nTotal properties scraped: {len(properties)}")

    if properties:
        print("\nFirst 3 properties:")
        for prop in properties[:3]:
            print(f"  {prop}")
