#!/usr/bin/env python3
"""
Setup script for Gemini API key and testing the RAG system.
Run this from the processing/ directory.
"""

import os
import json
import getpass

def setup_gemini_api_key():
    """Set up the Gemini API key."""
    print("=== Gemini API Key Setup ===")
    
    # Check if already set
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        print(f"✓ Gemini API key already set: {api_key[:10]}...")
        return api_key
    
    # Get API key from user
    print("Please enter your Gemini API key:")
    api_key = getpass.getpass("API Key: ").strip()
    
    if not api_key:
        print("⚠ No API key provided. You can set it later with:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        return None
    
    # Set environment variable for current session
    os.environ['GEMINI_API_KEY'] = api_key
    
    # Save to .env file in parent directory
    env_file = os.path.join('..', '.env')
    with open(env_file, 'w') as f:
        f.write(f"GEMINI_API_KEY={api_key}\n")
    
    print(f"✓ API key saved to {env_file}")
    print(f"✓ Environment variable set for current session")
    return api_key

def test_rag_system():
    """Test the RAG system with sample data."""
    print("\n=== Testing RAG System ===")
    
    # Check if properties file exists
    properties_file = os.path.join('..', 'data', 'unique_properties.json')
    if not os.path.exists(properties_file):
        print("⚠ Properties file not found. Creating sample data...")
        create_sample_data(properties_file)
    
    # Test RAG system
    try:
        from rag import PropertyRAG
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            print("⚠ No API key set. Testing with fallback mode...")
            api_key = None
        
        rag_system = PropertyRAG(properties_file, api_key)
        
        # Test query
        test_query = "apartments in Kathmandu"
        print(f"\nTesting query: '{test_query}'")
        
        retrieved_props = rag_system.retrieve_properties(test_query, top_k=3)
        if retrieved_props:
            print(f"✓ Found {len(retrieved_props)} properties")
            for i, prop in enumerate(retrieved_props):
                print(f"  {i+1}. {prop['title']} (Score: {prop['similarity_score']:.2f})")
            
            # Test Gemini response
            if rag_system.gemini_model:
                print("\n✓ Testing Gemini API response...")
                answer = rag_system.generate_answer_with_gemini(test_query, retrieved_props)
                print("Gemini Response:")
                print(answer[:200] + "..." if len(answer) > 200 else answer)
            else:
                print("\n⚠ Gemini API not available. Using fallback response.")
                answer = rag_system.generate_fallback_answer(test_query, retrieved_props)
                print("Fallback Response:")
                print(answer[:200] + "..." if len(answer) > 200 else answer)
        else:
            print("⚠ No properties found for test query")
            
    except Exception as e:
        print(f"✗ Error testing RAG system: {e}")
        return False
    
    return True

def create_sample_data(filepath):
    """Create sample property data for testing."""
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
            "scrapedAt": "2025-06-21T12:00:00Z",
            "source": "realestateinnepal.com"
        },
        {
            "id": "test-2", 
            "title": "Luxury Villa in Dubai",
            "price": 4500000,
            "currency": "AED",
            "location_raw": "Dubai Marina, Dubai",
            "full_address": "Dubai Marina, Dubai, UAE",
            "description": "Spacious luxury villa with garden and parking space.",
            "bedrooms": 4,
            "bathrooms": 3,
            "areaSqFt": 2500,
            "url": "https://www.realestate.com.au/international/ae/test-2",
            "extracted_amenities": ["Garden", "Parking", "Security", "Swimming Pool"],
            "scrapedAt": "2025-06-21T12:00:00Z",
            "source": "realestate.com.au/dubai"
        }
    ]
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Sample data created: {filepath}")

def main():
    print("=== Real Estate Insights Setup ===")
    print("This script will set up your Gemini API key and test the RAG system.\n")
    
    # Step 1: Setup API key
    api_key = setup_gemini_api_key()
    
    # Step 2: Test RAG system
    success = test_rag_system()
    
    print("\n=== Setup Complete ===")
    if success:
        print("✓ Everything is working! You can now:")
        print("  1. Run the RAG system: python rag.py")
        print("  2. Run the full pipeline: cd ../pipeline && go run pipeline.go")
        print("  3. Use the frontend to fetch property details")
    else:
        print("⚠ Some issues found. Please check the errors above.")
    
    print(f"\nYour Gemini API key is: {'Set' if api_key else 'Not set'}")

if __name__ == "__main__":
    main() 