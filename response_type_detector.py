"""
Response Type Detection
Determines what type of response the user wants (TABLE, CHART, or TEXT) based on their query
"""

import asyncio
import time
from ollama_client.ollama_client import OllamaClient


async def detect_response_type(user_query: str, data_records: list) -> str:
    """Detect what type of response the user wants based on their query."""
    max_retries = 3
    retry_delay = 1  # seconds
    start_time = time.time()
    
    for attempt in range(max_retries):
        attempt_start = time.time()
        
        try:
            ollama_client = OllamaClient()
            
            # Create a prompt to determine response type
            response_type_prompt = f"""
You are a response type detector. Based on the user's query, determine what type of response they want.

User Query: "{user_query}"

Available Response Types:
1. TABLE - User wants to see data in a structured table format (e.g., "show me", "list", "get", "find", "display", "events", "logs", "records")
2. CHART - User wants to visualize data in charts/graphs (e.g., "chart", "graph", "plot", "visualize", "trend", "over time")
3. TEXT - User wants a summary or description (e.g., "summarize", "summarise", "describe", "explain", "what is", "how many", "give me a summary", "tell me about")

CRITICAL RULE: If the query contains "list", "events", "logs", or "records" and asks to see data, it should be TABLE, not TEXT.

CRITICAL: You must respond with EXACTLY one of these three words: TABLE, CHART, or TEXT

IMPORTANT: Pay special attention to words like:
- "summarize", "summarise", "summary" → TEXT
- "describe", "explain", "what is" → TEXT  
- "how many", "total", "count" → TEXT
- "chart", "graph", "plot" → CHART
- "show me", "list", "get", "find", "display" → TABLE
- "events", "logs", "records" → TABLE (when asking to see data)

CRITICAL EXAMPLES:
- "Show me all violated rules" → TABLE
- "Create a chart of violations over time" → CHART  
- "Summarize the current rule status" → TEXT
- "Summarise the events for channel EMAIL" → TEXT
- "Plot the trend of alerts by priority" → CHART
- "List all monitors" → TABLE
- "List of events for Channel EMAIL" → TABLE
- "Give me the list of events" → TABLE
- "Show me events from last week" → TABLE
- "Get all logs" → TABLE
- "Explain what happened yesterday" → TEXT
- "Give me a summary of violations" → TEXT
- "Give me a summary of all rules" → TEXT
- "Summarize all rules" → TEXT
- "Summary of rules" → TEXT

Your response must be exactly one word: TABLE, CHART, or TEXT

Response type:"""

            response_type = await ollama_client.classify_intent(response_type_prompt)
            
            if response_type:
                # Clean and normalize the response
                detected_type = response_type.strip().upper()
                
                # Try to extract just the response type if LLM added extra text
                if len(detected_type) > 10:  # If response is too long, try to extract the type
                    if 'TABLE' in detected_type:
                        detected_type = 'TABLE'
                    elif 'CHART' in detected_type:
                        detected_type = 'CHART'
                    elif 'TEXT' in detected_type:
                        detected_type = 'TEXT'
                
                # Check if it's a valid response type
                if detected_type in ['TABLE', 'CHART', 'TEXT']:
                    return detected_type
                else:
                    # Don't retry for invalid response types, throw error
                    raise ValueError(f"LLM returned invalid response type: '{detected_type}'. Expected: TABLE, CHART, or TEXT")
            else:
                # Don't retry for empty responses, throw error
                raise ValueError("LLM returned empty response for response type detection")
                
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Check if it's a connection error
            if "ConnectError" in error_msg or "connection" in error_msg.lower():
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise ConnectionError(f"Failed to connect to Ollama after {max_retries} attempts: {error_msg}")
            else:
                # For non-connection errors, don't retry
                raise e
    
    # This should never be reached, but just in case
    raise ConnectionError(f"Failed to connect to Ollama after {max_retries} attempts")
