"""
Group Classification - First level intent classification
Determines which group (MONITOR_GROUP, FACTS_GROUP, RULES_GROUP, ACTIONS_GROUP) a query belongs to
"""

import asyncio
import time
from ollama_client.ollama_client import OllamaClient


async def classify_group(user_query: str) -> str:
    """Classify which group the user query belongs to."""
    print(f"🔍 Starting group classification for query: '{user_query}'")
    
    max_retries = 3
    retry_delay = 1  # seconds
    start_time = time.time()
    
    for attempt in range(max_retries):
        attempt_start = time.time()
        print(f"\n🔄 === OLLAMA GROUP CLASSIFICATION ATTEMPT {attempt + 1}/{max_retries} ===")
        print(f"⏱️  Attempt started at: {time.strftime('%H:%M:%S')}")
        
        try:
            print(f"🔌 Initializing Ollama client...")
            ollama_client = OllamaClient()
            print(f"✅ Ollama client initialized successfully")
            
            group_classification_prompt = f"""
You are a group classifier for a monitoring system. Based on the user's query, determine which group it belongs to:

MONITOR_GROUP: Queries about monitor configuration, setup, and definitions
- Monitor details, names, descriptions, and configuration
- Monitor status (enabled/disabled), types, and settings
- Monitor conditions and filtering logic
- Examples: "show monitors", "enabled monitors", "monitor configuration", "monitor details", "monitor conditions", "monitor setup"

FACTS_GROUP: Queries about actual events, feeds, and performance data
- Real-time events and feeds from different systems
- Performance metrics, throughput, and measured values
- Event counts and data that qualified monitor conditions
- Examples: "show events", "performance data", "event counts", "feeds from systems", "monitor events", "throughput data"
- NOTE: NOT about notification channels (EMAIL, SLACK, SMS) - those go to RULES_GROUP

RULES_GROUP: Queries about business rules, violations, and rule logic
- Rule definitions, status, and configuration
- Rule violation status and current state
- Rule evaluation logic and SQL definitions
- Rule actions and responses
- NOTIFICATION CHANNELS (EMAIL, SLACK, SMS, PAGERDUTY, OPSGENIE) - these are about rule violation alerts
- Examples: "show rules", "violated rules", "rule status", "rule configuration", "rule actions", "rule violations", "EMAIL notifications", "SLACK alerts", "channel EMAIL", "notifications via SMS"

ACTIONS_GROUP: Queries about available actions and action execution
- Available action types and executors
- Action configurations and settings
- Examples: "show actions", "available actions", "action types", "action executors"

Key distinctions:
- "monitors" or "monitor configuration" = MONITOR_GROUP
- "events", "feeds", "performance data" = FACTS_GROUP  
- "rules", "violations", "rule logic" = RULES_GROUP
- "channels" (EMAIL, SLACK, SMS, PAGERDUTY, OPSGENIE) = RULES_GROUP (rule violation notifications)
- "actions", "action types" = ACTIONS_GROUP

CRITICAL: Look for context words to determine the group:
- "monitor", "configuration", "setup" → MONITOR_GROUP
- "events", "feeds", "performance", "throughput" → FACTS_GROUP
- "rules", "violations", "rule logic" → RULES_GROUP
- "channels" (EMAIL, SLACK, SMS, PAGERDUTY, OPSGENIE) → RULES_GROUP (rule violation notifications)
- "actions", "action types" → ACTIONS_GROUP

User Query: "{user_query}"

IMPORTANT EXAMPLES:
- "Show me all monitors" → MONITOR_GROUP
- "Show me events from last week" → FACTS_GROUP
- "Which rules are violated?" → RULES_GROUP
- "What actions are available?" → ACTIONS_GROUP
- "Monitor configuration for SAP" → MONITOR_GROUP
- "Performance data for CPU monitor" → FACTS_GROUP
- "Rule violation history" → RULES_GROUP
- "Available action executors" → ACTIONS_GROUP
- "Plot me a chart for Channel EMAIL" → RULES_GROUP (channels are about rule violations)
- "EMAIL notifications for last week" → RULES_GROUP (rule violation notifications)
- "SLACK alerts" → RULES_GROUP (rule violation notifications)

Respond with EXACTLY one of these options:
MONITOR_GROUP
FACTS_GROUP
RULES_GROUP
ACTIONS_GROUP

Group choice:"""

            print(f"📝 Prompt created, length: {len(group_classification_prompt)} characters")
            print(f"🚀 Sending request to Ollama...")
            
            group_choice = await ollama_client.classify_intent(group_classification_prompt)
            
            if not group_choice:
                print("⚠️ LLM returned empty response")
                # Don't retry for empty responses, throw error
                raise ValueError("LLM returned empty response for group classification")
            
            # Clean and normalize the response
            detected_group = group_choice.strip().upper()
            print(f"🔍 Raw group classification: '{detected_group}'")
            
            # Try to extract just the group if LLM added extra text
            if len(detected_group) > 15:  # If response is too long, try to extract the group
                print("🔍 Response seems long, attempting to extract group...")
                if 'MONITOR_GROUP' in detected_group:
                    detected_group = 'MONITOR_GROUP'
                elif 'FACTS_GROUP' in detected_group:
                    detected_group = 'FACTS_GROUP'
                elif 'RULES_GROUP' in detected_group:
                    detected_group = 'RULES_GROUP'
                elif 'ACTIONS_GROUP' in detected_group:
                    detected_group = 'ACTIONS_GROUP'
                print(f"🔍 Extracted group: '{detected_group}'")
            
            # Check if it's a valid group
            if detected_group in ['MONITOR_GROUP', 'FACTS_GROUP', 'RULES_GROUP', 'ACTIONS_GROUP']:
                attempt_duration = time.time() - attempt_start
                total_duration = time.time() - start_time
                print(f"🎯 SUCCESS: Group classification successful: {detected_group}")
                print(f"⏱️  Attempt {attempt + 1} duration: {attempt_duration:.2f}s")
                print(f"⏱️  Total time: {total_duration:.2f}s")
                return detected_group
            else:
                print(f"⚠️ LLM returned invalid group: '{detected_group}'")
                # Don't retry for invalid responses, throw error
                raise ValueError(f"LLM returned invalid group: '{detected_group}'. Expected one of: MONITOR_GROUP, FACTS_GROUP, RULES_GROUP, ACTIONS_GROUP")
                
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
