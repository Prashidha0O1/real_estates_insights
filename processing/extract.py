import json
import re
import spacy
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# Load spaCy model (download if not present: python -m spacy download en_core_web_sm)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spaCy model 'en_core_web_sm'...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")


geolocator = Nominatim(user_agent="real-estate-insights-app")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def load_properties(filepath):
    """Loads properties from a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_text(text):
    """Basic text cleaning."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r'\s+', ' ', text).strip() # Replace multiple spaces with single
    text = text.lower() # Convert to lowercase for consistency
    return text

def extract_amenities(description):
    """Extracts potential amenities from description using simple keyword matching."""
    amenities = []
    description = clean_text(description)
    if "swimming pool" in description:
        amenities.append("swimming pool")
    if "gym" in description or "fitness center" in description:
        amenities.append("gym")
    if "parking" in description or "garage" in description:
        amenities.append("parking")
    if "garden" in description:
        amenities.append("garden")
    return list(set(amenities)) # Return unique amenities

def geocode_location(location_str):
    """Geocodes a location string to lat/lon."""
    try:
        if location_str:
            # Add a country context for better accuracy, e.g., "Nepal"
            full_address = f"{location_str}, Nepal" # Adjust based on your target country
            location = geocode(full_address, timeout=10)
            if location:
                return {"latitude": location.latitude, "longitude": location.longitude, "address": location.address}
    except Exception as e:
        print(f"Error geocoding '{location_str}': {e}")
    return {"latitude": None, "longitude": None, "address": None}

def process_property(property_data):
    """Processes a single property for cleaner data and extractions."""
    processed = property_data.copy()
    processed['title'] = clean_text(processed.get('title', ''))
    processed['description'] = clean_text(processed.get('description', ''))
    processed['location_raw'] = processed.get('location', '') # Keep raw location
    processed['extracted_amenities'] = extract_amenities(processed.get('description', ''))

    # Geocode if location_raw is present and not already geocoded
    if processed.get('location_raw') and (processed.get('latitude') is None or processed.get('longitude') is None):
        geo_info = geocode_location(processed['location_raw'])
        processed['latitude'] = geo_info['latitude']
        processed['longitude'] = geo_info['longitude']
        processed['full_address'] = geo_info['address']
    else:
        # If no raw location or already geocoded (from previous runs or manual input)
        processed['latitude'] = processed.get('latitude')
        processed['longitude'] = processed.get('longitude')
        processed['full_address'] = processed.get('full_address')

    return processed

def main():
    input_filepath = '../data/properties.json'
    output_filepath = '../data/processed_properties.json'

    properties = load_properties(input_filepath)
    processed_properties = []

    print(f"Processing {len(properties)} properties...")
    for i, prop in enumerate(properties):
        processed_prop = process_property(prop)
        processed_properties.append(processed_prop)
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1} properties...")

    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(processed_properties, f, indent=2, ensure_ascii=False)

    print(f"Processing complete. Cleaned and extracted data saved to {output_filepath}")

main()