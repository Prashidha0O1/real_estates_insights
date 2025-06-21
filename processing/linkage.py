import json
from collections import defaultdict
from fuzzywuzzy import fuzz 
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import euclidean
import numpy as np

def load_processed_properties(filepath):
    """Loads processed properties from a JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def jaccard_similarity(s1, s2):
    """Calculates Jaccard similarity between two sets."""
    set1 = set(s1.lower().split())
    set2 = set(s2.lower().split())
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union != 0 else 0

def calculate_text_similarity(text1, text2):
    """Calculates a combined text similarity score."""
    if not text1 or not text2:
        return 0.0
    
    fuzz_ratio = fuzz.ratio(text1, text2) / 100.0
    return fuzz_ratio 

def calculate_geographic_distance(prop1, prop2):
    """Calculates Euclidean distance between two property locations (if available)."""
    lat1, lon1 = prop1.get('latitude'), prop1.get('longitude')
    lat2, lon2 = prop2.get('latitude'), prop2.get('longitude')

    if None in [lat1, lon1, lat2, lon2]:
        return float('inf') 
    return euclidean([lat1, lon1], [lat2, lon2])

def find_duplicates_blocking(properties, price_tolerance=0.05, text_threshold=0.8, geo_distance_threshold=0.01):
    """
    Finds duplicate properties using a blocking approach.
    Blocks by location and then compares within blocks.
    """
    potential_duplicates = defaultdict(list)
    final_unique_properties = []
    merged_ids = set()
    for prop in properties:
        if prop['location_raw']:
            block_key = " ".join(prop['location_raw'].lower().split()[:2]) # Example: "Kathmandu, Nepal" -> "kathmandu nepal"
            potential_duplicates[block_key].append(prop)

    for block_key, block_props in potential_duplicates.items():
        if len(block_props) < 2:
            for prop in block_props:
                if prop['id'] not in merged_ids:
                    final_unique_properties.append(prop)
            continue
        for i in range(len(block_props)):
            prop1 = block_props[i]
            if prop1['id'] in merged_ids:
                continue 

            found_match = False
            for j in range(i + 1, len(block_props)):
                prop2 = block_props[j]
                if prop2['id'] in merged_ids:
                    continue

                
                price_diff_ratio = abs(prop1['price'] - prop2['price']) / ((prop1['price'] + prop2['price']) / 2) if (prop1['price'] + prop2['price']) / 2 != 0 else 1.0
                title_similarity = calculate_text_similarity(prop1['title'], prop2['title'])
                desc_similarity = calculate_text_similarity(prop1['description'], prop2['description'])
                geo_distance = calculate_geographic_distance(prop1, prop2) # In degrees if lat/lon are degrees

                is_price_similar = price_diff_ratio < price_tolerance
                is_text_similar = (title_similarity > text_threshold or desc_similarity > text_threshold)
                is_geo_close = geo_distance < geo_distance_threshold # Adjust this threshold based on typical property area
                if is_price_similar and (is_text_similar or is_geo_close):
                    print(f"Merging: '{prop1['title']}' (ID: {prop1['id']}) and '{prop2['title']}' (ID: {prop2['id']})")
                    merged_ids.add(prop2['id'])
                    found_match = True
            
            if prop1['id'] not in merged_ids: # Add prop1 if it wasn't merged into another, or wasn't a duplicate itself
                final_unique_properties.append(prop1)

    return final_unique_properties


def main():
    input_filepath = '../data/processed_properties.json'
    output_filepath = '../data/unique_properties.json'

    properties = load_processed_properties(input_filepath)
    print(f"Loaded {len(properties)} properties for linkage.")

    unique_properties = find_duplicates_blocking(properties)

    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(unique_properties, f, indent=2, ensure_ascii=False)

    print(f"Record linkage complete. Found {len(unique_properties)} unique properties (from {len(properties)}).")
    print(f"Unique properties saved to {output_filepath}")

main()