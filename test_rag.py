#!/usr/bin/env python3
"""
Test script for the Real Estate RAG system with Gemini API integration.
"""

import os
import sys
sys.path.append('processing')

from rag import PropertyRAG

def test_rag_system():
    """Test the RAG system with sample data."""
    
    # Get Gemini API key
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        print("Please set your Gemini API key as an environment variable:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        print("Or run: set GEMINI_API_KEY=your-api-key-here (on Windows)")
        return
    
    # Test with sample data if no properties file exists
    properties_file = 'data/unique_properties.json'
    if not os.path.exists(properties_file):
        print(f"Properties file not found: {properties_file}")
        print("Creating sample data for testing...")
        
        # Create sample data
        sample_data = [
            {
                "id": "test-1",
                "title": "Modern Apartment in Kathmandu",
                "price": 25000000,
                "currency": "NPR",
                "location_raw": "Thamel, Kathmandu",
                "full_address": "Thamel, Kathmandu, Nepal",
                "description": "Beautiful modern apartment in the heart of Thamel with all amenities.",
                "bedrooms": 2,
                "bathrooms": 2,
                "areaSqFt": 1200,
                "url": "https://www.realestateinnepal.com/property/test-1",
                "extracted_amenities": ["Parking", "Garden", "Security"],
                "scrapedAt": "2025-06-21T12:00:00Z"
            },
            {
                "id": "test-2", 
                "title": "Luxury Villa in Lalitpur",
                "price": 45000000,
                "currency": "NPR",
                "location_raw": "Patan, Lalitpur",
                "full_address": "Patan, Lalitpur, Nepal",
                "description": "Spacious luxury villa with garden and parking space.",
                "bedrooms": 4,
                "bathrooms": 3,
                "areaSqFt": 2500,
                "url": "https://www.realestateinnepal.com/property/test-2",
                "extracted_amenities": ["Garden", "Parking", "Security", "Swimming Pool"],
                "scrapedAt": "2025-06-21T12:00:00Z"
            }
        ]
        
        # Save sample data
        import json
        os.makedirs('data', exist_ok=True)
        with open(properties_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)
        
        print(f"Created sample data in {properties_file}")
    
    # Initialize RAG system
    print("Initializing RAG system...")
    rag_system = PropertyRAG(properties_file, gemini_api_key)
    
    # Test queries
    test_queries = [
        "apartments in Kathmandu",
        "luxury properties with swimming pool",
        "affordable houses for sale",
        "properties with parking space"
    ]
    
    print("\n=== Testing RAG System ===")
    for query in test_queries:
        print(f"\n--- Query: '{query}' ---")
        
        # Retrieve properties
        retrieved_props = rag_system.retrieve_properties(query, top_k=3)
        
        if retrieved_props:
            print(f"Found {len(retrieved_props)} relevant properties:")
            for i, prop in enumerate(retrieved_props):
                print(f"  {i+1}. {prop['title']} (Score: {prop['similarity_score']:.2f})")
            
            # Generate answer with Gemini
            print("\nAI Analysis:")
            if rag_system.gemini_model:
                answer = rag_system.generate_answer_with_gemini(query, retrieved_props)
                print(answer)
            else:
                print("Gemini API not available, using fallback response.")
                answer = rag_system.generate_fallback_answer(query, retrieved_props)
                print(answer)
        else:
            print("No relevant properties found.")
        
        print("-" * 50)

if __name__ == "__main__":
    test_rag_system() 