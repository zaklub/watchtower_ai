"""
Ollama-based intent classification logic
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import INTENT_CLASSIFICATION_PROMPT
from ollama_client.ollama_client import OllamaClient
from .fallback_intent_classification import fallback_intent_classification


async def classify_intent(query: str) -> str:
    """
    Use Ollama to classify the intent of the query into one of three categories:
    1. monitoring_details - Get monitoring data/reports
    2. create_rule - Create new monitoring rules/alerts  
    3. generic_question - General questions about capabilities
    
    Args:
        query: The user's query string
        
    Returns:
        str: The classified intent
    """
    
    print(f"🎯 Starting intent classification for query: '{query}'")
    
    # Create Ollama client
    ollama_client = OllamaClient()
    
    # Prepare prompt
    prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
    
    # Try Ollama classification
    raw_response = await ollama_client.classify_intent(prompt)
    
    if raw_response is not None:
        intent = raw_response.strip().lower()
        print(f"🔧 Processed intent: '{intent}'")
        
        # Validate intent
        valid_intents = ["monitoring_details", "create_rule", "generic_question"]
        if intent in valid_intents:
            print(f"✅ Valid intent detected: {intent}")
            return intent
        else:
            print(f"⚠️ Invalid intent from Ollama: '{intent}', falling back to keyword matching")
            fallback_result = fallback_intent_classification(query)
            print(f"🔤 Fallback result: {fallback_result}")
            return fallback_result
    else:
        print("🔤 Ollama failed, falling back to keyword matching")
        fallback_result = fallback_intent_classification(query)
        print(f"🔤 Fallback result: {fallback_result}")
        return fallback_result
