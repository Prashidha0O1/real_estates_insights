#!/usr/bin/env python3
"""
Configuration file for Real Estate Insights project.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

# Data paths
DATA_DIR = os.getenv('DATA_DIR', './data')
PROPERTIES_FILE = os.path.join(DATA_DIR, 'unique_properties.json')
PROCESSED_FILE = os.path.join(DATA_DIR, 'processed_properties.json')
KG_FILE = os.path.join(DATA_DIR, 'real_estate_kg.json')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

def check_gemini_api_key():
    """Check if Gemini API key is set."""
    if not GEMINI_API_KEY:
        print("⚠️  WARNING: GEMINI_API_KEY not set!")
        print("To set your Gemini API key, use one of these methods:")
        print()
        print("Method 1 - Environment variable (Git Bash):")
        print("export GEMINI_API_KEY='your-api-key-here'")
        print()
        print("Method 2 - Environment variable (Windows CMD):")
        print("set GEMINI_API_KEY=your-api-key-here")
        print()
        print("Method 3 - Create a .env file in the project root:")
        print("echo 'GEMINI_API_KEY=your-api-key-here' > .env")
        print()
        print("Method 4 - Set it when running the script:")
        print("GEMINI_API_KEY=your-api-key-here python test_rag.py")
        return False
    else:
        print("✓ Gemini API key is configured")
        return True

if __name__ == "__main__":
    check_gemini_api_key() 