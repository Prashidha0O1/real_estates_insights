import json
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
import google.generativeai as genai
from typing import List, Dict, Any

# Configure Gemini API
def setup_gemini(api_key: str):
    """Setup Gemini API with the provided API key."""
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel('gemini-pro')
        return model
    except Exception as e:
        print(f"Error setting up Gemini: {e}")
        return None

# Load a pre-trained sentence transformer model
try:
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # Good balance of speed and performance
except Exception as e:
    print(f"Could not load SentenceTransformer model. Please ensure you have internet or download it manually. Error: {e}")
    print("Trying a different model or skipping embedding for now.")
    embedding_model = None

class PropertyRAG:
    def __init__(self, properties_filepath: str, gemini_api_key: str = None):
        self.properties = self._load_properties(properties_filepath)
        self.embeddings = None
        self.gemini_model = None
        
        if gemini_api_key:
            self.gemini_model = setup_gemini(gemini_api_key)
        
        if embedding_model:
            self._generate_embeddings()

    def _load_properties(self, filepath: str) -> List[Dict[str, Any]]:
        """Load properties from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Properties file not found: {filepath}")
            return []
        except json.JSONDecodeError:
            print(f"Invalid JSON in properties file: {filepath}")
            return []

    def _generate_embeddings(self):
        """Generate embeddings for all properties."""
        print("Generating embeddings for properties...")
        texts = [
            f"Title: {prop.get('title', '')}. Description: {prop.get('description', '')}. Location: {prop.get('location_raw', prop.get('location', ''))}. Amenities: {', '.join(prop.get('extracted_amenities', []))}"
            for prop in self.properties
        ]
        self.embeddings = embedding_model.encode(texts, show_progress_bar=True)
        print(f"Generated embeddings for {len(self.properties)} properties.")

    def retrieve_properties(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieves top_k most relevant properties for a given query."""
        if self.embeddings is None:
            print("Embeddings not generated. Cannot perform retrieval.")
            return []

        query_embedding = embedding_model.encode([query])[0]
        similarities = cosine_similarity([query_embedding], self.embeddings)[0]
        top_indices = np.argsort(similarities)[::-1][:top_k]

        retrieved_properties = []
        for idx in top_indices:
            prop = self.properties[idx].copy()
            prop['similarity_score'] = float(similarities[idx])
            retrieved_properties.append(prop)
        return retrieved_properties

    def generate_answer_with_gemini(self, query: str, retrieved_properties: List[Dict[str, Any]]) -> str:
        """Generate an answer using Gemini API based on retrieved properties."""
        if not self.gemini_model:
            return "Gemini API not configured. Please provide a valid API key."
        
        if not retrieved_properties:
            return "I could not find any relevant properties for your query."

        # Prepare context for Gemini
        context = "Here are some relevant property details:\n\n"
        for i, prop in enumerate(retrieved_properties):
            context += (
                f"Property {i+1} (Relevance Score: {prop['similarity_score']:.2f}):\n"
                f"- Title: {prop.get('title', 'N/A')}\n"
                f"- Location: {prop.get('full_address', prop.get('location_raw', prop.get('location', 'N/A')))}\n"
                f"- Price: {prop.get('currency', '')} {prop.get('price', 'N/A'):,.0f if prop.get('price') else 'N/A'}\n"
                f"- Bedrooms: {prop.get('bedrooms', 'N/A')}\n"
                f"- Bathrooms: {prop.get('bathrooms', 'N/A')}\n"
                f"- Area: {prop.get('areaSqFt', 'N/A')} sqft\n"
                f"- Amenities: {', '.join(prop.get('extracted_amenities', []))}\n"
                f"- Description: {prop.get('description', 'N/A')[:200]}...\n\n"
            )

        # Create prompt for Gemini
        prompt = f"""
You are a real estate expert assistant. Based on the following property information, please answer the user's query: "{query}"

{context}

Please provide a helpful, informative response that:
1. Directly addresses the user's query
2. Highlights the most relevant properties
3. Provides insights about pricing, location, and features
4. Suggests what to consider when making a decision

Answer:"""

        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return self.generate_fallback_answer(query, retrieved_properties)

    def generate_fallback_answer(self, query: str, retrieved_properties: List[Dict[str, Any]]) -> str:
        """Generate a fallback answer when Gemini is not available."""
        answer = f"Based on the available property data for your query: '{query}', here are some insights:\n\n"
        
        for i, prop in enumerate(retrieved_properties):
            answer += (
                f"Property {i+1} is a '{prop.get('title', 'N/A')}' located in "
                f"'{prop.get('full_address', prop.get('location_raw', prop.get('location', 'N/A')))}' "
                f"for {prop.get('currency', '')} {prop.get('price', 'N/A'):,.0f if prop.get('price') else 'N/A'}. "
                f"It has {prop.get('bedrooms', 'N/A')} bedrooms and {prop.get('bathrooms', 'N/A')} bathrooms. "
                f"Key amenities include: {', '.join(prop.get('extracted_amenities', ['None']))}.\n\n"
            )
        
        answer += "For more details, please refer to the specific listings."
        return answer

def main():
    # Get Gemini API key from environment or user input
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        gemini_api_key = input("Enter your Gemini API key (or press Enter to skip): ").strip()
        if gemini_api_key:
            os.environ['GEMINI_API_KEY'] = gemini_api_key

    properties_filepath = '../data/unique_properties.json'
    rag_system = PropertyRAG(properties_filepath, gemini_api_key)

    print("\n=== Real Estate RAG System ===")
    print("Enter your property query (e.g., 'apartments with pool in Kathmandu' or 'house near schools')")
    print("Type 'exit' to quit\n")

    while True:
        query = input("> ")
        if query.lower() == 'exit':
            break

        retrieved_props = rag_system.retrieve_properties(query, top_k=5)
        if retrieved_props:
            print(f"\n--- Found {len(retrieved_props)} Relevant Properties ---")
            for i, prop in enumerate(retrieved_props):
                print(f"{i+1}. {prop['title']} - {prop.get('location_raw', prop.get('location', 'N/A'))} "
                      f"- {prop.get('currency', '')} {prop.get('price', 'N/A'):,.0f if prop.get('price') else 'N/A'} "
                      f"(Score: {prop['similarity_score']:.2f})")
            
            print("\n--- AI Analysis ---")
            if rag_system.gemini_model:
                answer = rag_system.generate_answer_with_gemini(query, retrieved_props)
            else:
                answer = rag_system.generate_fallback_answer(query, retrieved_props)
            print(answer)
        else:
            print("No relevant properties found for your query.")

if __name__ == "__main__":
    main()