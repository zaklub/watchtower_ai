"""
Ollama-based intent classification logic
"""

import sys
import os
import asyncio
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import INTENT_CLASSIFICATION_PROMPT
from ollama_client.ollama_client import OllamaClient


async def classify_intent(query: str) -> str:
    """
    Use Ollama to classify the intent of the query into one of four categories:
    1. monitoring_details - Get monitoring data/reports
    2. create_rule - Create new monitoring rules/alerts  
    3. generic_question - General questions about capabilities
    4. database_schema - Queries about database structure/tables/schema
    
    Args:
        query: The user's query string
        
    Returns:
        str: The classified intent
    """
    
    print(f"🎯 Starting intent classification for query: '{query}'")
    
    max_retries = 3
    retry_delay = 1  # seconds
    start_time = time.time()
    
    for attempt in range(max_retries):
        attempt_start = time.time()
        print(f"\n🔄 === OLLAMA INTENT CLASSIFICATION ATTEMPT {attempt + 1}/{max_retries} ===")
        print(f"⏱️  Attempt started at: {time.strftime('%H:%M:%S')}")
        
        try:
            # Create Ollama client
            print(f"🔌 Initializing Ollama client...")
            ollama_client = OllamaClient()
            print(f"✅ Ollama client initialized successfully")
            
            # Prepare prompt
            prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
            print(f"📝 Prompt created, length: {len(prompt)} characters")
            print(f"🚀 Sending request to Ollama...")
            
            # Try Ollama classification
            raw_response = await ollama_client.classify_intent(prompt)
            
            if raw_response is not None:
                intent = raw_response.strip().lower()
                print(f"🔧 Processed intent: '{intent}'")
                
                # Validate intent
                valid_intents = ["monitoring_details", "create_rule", "generic_question", "database_schema"]
                if intent in valid_intents:
                    attempt_duration = time.time() - attempt_start
                    total_duration = time.time() - start_time
                    print(f"🎯 SUCCESS: Valid intent detected: {intent}")
                    print(f"⏱️  Attempt {attempt + 1} duration: {attempt_duration:.2f}s")
                    print(f"⏱️  Total time: {total_duration:.2f}s")
                    return intent
                else:
                    print(f"⚠️ Invalid intent from Ollama: '{intent}'")
                    # Don't retry for invalid responses, throw error
                    raise ValueError(f"LLM returned invalid intent: '{intent}'. Expected one of: {valid_intents}")
            else:
                print("⚠️ LLM returned empty response")
                # Don't retry for empty responses, throw error
                raise ValueError("LLM returned empty response for intent classification")
                
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            attempt_duration = time.time() - attempt_start
            print(f"❌ Attempt {attempt + 1} FAILED after {attempt_duration:.2f}s")
            print(f"❌ Error type: {error_type}")
            print(f"❌ Error message: {error_msg}")
            
            # Check if it's a connection error
            if "ConnectError" in error_msg or "connection" in error_msg.lower():
                if attempt < max_retries - 1:
                    print(f"🔄 Connection error detected - this is retryable")
                    print(f"⏳ Waiting {retry_delay} seconds before retry...")
                    await asyncio.sleep(retry_delay)
                    print(f"🔄 Retry delay completed, proceeding to attempt {attempt + 2}")
                    retry_delay *= 2  # Exponential backoff
                else:
                    total_duration = time.time() - start_time
                    print(f"💥 ALL {max_retries} CONNECTION ATTEMPTS FAILED")
                    print(f"⏱️  Total time spent: {total_duration:.2f}s")
                    print(f"💥 Raising ConnectionError to frontend")
                    raise ConnectionError(f"Failed to connect to Ollama after {max_retries} attempts: {error_msg}")
            else:
                # For non-connection errors, don't retry
                print(f"💥 Non-connection error detected - not retrying")
                print(f"💥 Raising error to frontend: {error_type}")
                raise e
    
    # This should never be reached, but just in case
    total_duration = time.time() - start_time
    print(f"💥 UNEXPECTED: Function completed without return or exception")
    print(f"⏱️  Total time spent: {total_duration:.2f}s")
    raise ConnectionError(f"Failed to connect to Ollama after {max_retries} attempts")
