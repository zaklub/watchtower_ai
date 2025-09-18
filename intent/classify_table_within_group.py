"""
Table Classification Within Group - Second level intent classification
Determines which specific table within a group should handle the query, or if it should use analytics

ENHANCED CLASSIFICATION SYSTEM:
- MONITOR_GROUP: Basic monitor tables + Analytics
- FACTS_GROUP: Event data tables + Analytics  
- RULES_GROUP: Three-level classification system:
  1. Level 1: Group Classification (RULES_GROUP)
  2. Level 2: Data Type Classification (CURRENT_DATA vs HISTORICAL_DATA)
  3. Level 3: Table/Analytics Classification:
     - CURRENT_DATA: MONITOR_RULES, RULES_DEFINITIONS, RULES_ACTIONS, ACTION_EXECUTORS, or Analytics
     - HISTORICAL_DATA: MONITOR_RULES_LOGS or Analytics
     - Analytics classification is handled within each data type function
- ACTIONS_GROUP: Action tables + Analytics
"""

import asyncio
import time
from ollama_client.ollama_client import OllamaClient


async def classify_table_within_group(group: str, user_query: str) -> str:
    """Classify which table within a group should handle the query, or if it should use analytics."""
    print(f"🔍 Starting table classification for group: {group}, query: '{user_query}'")
    
    max_retries = 3
    retry_delay = 1  # seconds
    start_time = time.time()
    
    for attempt in range(max_retries):
        attempt_start = time.time()
        print(f"\n🔄 === OLLAMA TABLE CLASSIFICATION ATTEMPT {attempt + 1}/{max_retries} ===")
        print(f"⏱️  Attempt started at: {time.strftime('%H:%M:%S')}")
        
        try:
            print(f"🔌 Initializing Ollama client...")
            ollama_client = OllamaClient()
            print(f"✅ Ollama client initialized successfully")
            
            # Create group-specific prompts
            if group == "MONITOR_GROUP":
                result = await _classify_monitor_group_tables(user_query, ollama_client)
            elif group == "FACTS_GROUP":
                result = await _classify_facts_group_tables(user_query, ollama_client)
            elif group == "RULES_GROUP":
                result = await _classify_rules_group_tables(user_query, ollama_client)
            elif group == "ACTIONS_GROUP":
                result = await _classify_actions_group_tables(user_query, ollama_client)
            else:
                print(f"⚠️ Unknown group: {group}, defaulting to analytics")
                result = "ANALYTICS"
            
            attempt_duration = time.time() - attempt_start
            total_duration = time.time() - start_time
            print(f"🎯 SUCCESS: Table classification successful: {result}")
            print(f"⏱️  Attempt {attempt + 1} duration: {attempt_duration:.2f}s")
            print(f"⏱️  Total time: {total_duration:.2f}s")
            return result
            
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


async def _classify_monitor_group_tables(user_query: str, ollama_client: OllamaClient) -> str:
    """Classify tables within MONITOR_GROUP."""
    prompt = f"""
You are a table classifier for the MONITOR_GROUP. Based on the user's query, determine which table to use:

MONITORED_FEEDS: Use for queries about monitor configuration and basic details
- Monitor names, descriptions, status (enabled/disabled)
- Monitor types and basic configuration
- Examples: "show monitors", "enabled monitors", "monitor names", "monitor status"

MONITOR_CONDITIONS: Use for queries about monitor filtering conditions
- Conditions that qualify incoming feeds as facts
- Monitor filtering logic and rules
- Examples: "monitor conditions", "filtering logic", "monitor filters", "qualification rules"

ANALYTICS: Use for complex queries that require joins or aggregations across monitor tables
- Queries with "most", "highest", "average", "count", "group by"
- Comparing monitors or analyzing monitor patterns
- Examples: "which monitors have most conditions", "average conditions per monitor", "monitor statistics"
- IMPORTANT: Ignore output format keywords like "plot", "chart", "graph", "list", "show" - these only affect response format, not data source

User Query: "{user_query}"

IMPORTANT EXAMPLES:
- "Show me all monitors" → MONITORED_FEEDS
- "Plot me a chart of all monitors" → MONITORED_FEEDS (same data, different output format)
- "Monitor configuration for SAP" → MONITORED_FEEDS
- "What conditions does monitor X have?" → MONITOR_CONDITIONS
- "Which monitors have the most conditions?" → ANALYTICS

Respond with EXACTLY one of these options:
MONITORED_FEEDS
MONITOR_CONDITIONS
ANALYTICS

Table choice:"""

    print(f"📝 Prompt created, length: {len(prompt)} characters")
    print(f"🚀 Sending request to Ollama...")
    
    table_choice = await ollama_client.classify_intent(prompt)
    
    if not table_choice:
        print("⚠️ LLM returned empty response")
        # Don't retry for empty responses, throw error
        raise ValueError("LLM returned empty response for table classification")
    
    return _normalize_table_choice(table_choice, ["MONITORED_FEEDS", "MONITOR_CONDITIONS", "ANALYTICS"])


async def _classify_facts_group_tables(user_query: str, ollama_client: OllamaClient) -> str:
    """Classify tables within FACTS_GROUP."""
    prompt = f"""
You are a table classifier for the FACTS_GROUP. Based on the user's query, determine which table to use:

MONITOR_FACTS: Use for queries about actual events, feeds, and performance data
- Real-time events that qualified monitor conditions
- Performance metrics, throughput, and measured values
- Event counts and data from different systems
- Examples: "show events", "performance data", "event counts", "feeds from systems", "monitor events"

ANALYTICS: Use for complex queries that require aggregations or analysis of facts data
- Queries with "most", "highest", "average", "count", "group by", "trends"
- Analyzing patterns in events or performance data
- Examples: "trend of events over time", "average performance by monitor", "event patterns"
- IMPORTANT: Ignore output format keywords like "plot", "chart", "graph", "list", "show" - these only affect response format, not data source

User Query: "{user_query}"

IMPORTANT EXAMPLES:
- "Show me events from last week" → MONITOR_FACTS
- "Performance data for CPU monitor" → MONITOR_FACTS
- "Plot me a chart of events from last week" → MONITOR_FACTS (same data, different output format)
- "Give me a list of monitors with feeds" → MONITOR_FACTS
- "Plot me a chart of monitors with feeds" → MONITOR_FACTS (same data, different output format)
- "Trend of events over time" → ANALYTICS
- "Average performance by monitor" → ANALYTICS

Respond with EXACTLY one of these options:
MONITOR_FACTS
ANALYTICS

Table choice:"""

    print(f"📝 Prompt created, length: {len(prompt)} characters")
    print(f"🚀 Sending request to Ollama...")
    
    table_choice = await ollama_client.classify_intent(prompt)
    
    if not table_choice:
        print("⚠️ LLM returned empty response")
        # Don't retry for empty responses, throw error
        raise ValueError("LLM returned empty response for table classification")
    
    return _normalize_table_choice(table_choice, ["MONITOR_FACTS", "ANALYTICS"])


async def _classify_rules_group_tables(user_query: str, ollama_client: OllamaClient) -> str:
    """Classify tables within RULES_GROUP using three-level classification system."""
    print(f"🔍 Starting RULES_GROUP classification with three-level system")
    
    # Step 1: Determine if this is CURRENT_DATA or HISTORICAL_DATA
    data_type = await _classify_rules_data_type(user_query, ollama_client)
    print(f"🎯 Data type classified as: {data_type}")
    
    # Step 2: Based on data type, classify specific table or analytics
    if data_type == "CURRENT_DATA":
        return await _classify_current_data_tables(user_query, ollama_client)
    elif data_type == "HISTORICAL_DATA":
        return await _classify_historical_data_tables(user_query, ollama_client)
    else:
        raise ValueError(f"Invalid data type: {data_type}")


async def _classify_rules_data_type(user_query: str, ollama_client: OllamaClient) -> str:
    """Level 2: Classify if the query is about CURRENT_DATA or HISTORICAL_DATA."""
    prompt = f"""
You are a data type classifier for the RULES_GROUP. Based on the user's query, determine the data type:

KEY DISTINCTION:
- CURRENT_DATA = What rules are configured to do NOW (current settings, configurations, available actions, rule SQL/logic definitions)
- HISTORICAL_DATA = What actually happened in the past (events, violations, notifications sent, rule execution results)

CRITICAL CLASSIFICATION RULES:

1. CURRENT_DATA - Use for queries about current/static information:
   - Current rule status, configuration, and settings
   - Rule definitions, logic, and SQL queries
   - Rule evaluation criteria and conditions
   - Current action configurations and what actions are available
   - Available action types and executors
   - Current violation status of rules (which rules are currently violated)
   - Examples: "show rules", "rule status", "rule configuration", "enabled rules", "active rules", "violated rules", "which rules are violated", "give me rules that are currently violated", "available actions", "action types", "rules whose actions are EMAIL", "rule SQL", "rule logic", "rule definition"

2. HISTORICAL_DATA - Use for queries about time-based events and history:
   - Rule violation history and audit trails
   - Past rule evaluations and results
   - Channel-specific events and notifications (EMAIL, SLACK, SMS, PAGERDUTY, OPSGENIE)
   - Examples: "rule history", "violation logs", "events for Channel EMAIL", "SLACK notifications", "what happened when", "show me events"

DECISION LOGIC:
- If query contains "current", "status", "configuration", "enabled", "active", "violated" → CURRENT_DATA
- If query contains "history", "events", "logs", "channel", "notifications" → HISTORICAL_DATA
- If query asks "what is" or "how does" → CURRENT_DATA
- If query asks "what happened" or "show me events" → HISTORICAL_DATA
- If query asks about "available actions" or "action types" → CURRENT_DATA
- If query asks "rules whose actions are X" → CURRENT_DATA (current configuration)
- If query asks "events for Channel X" → HISTORICAL_DATA (historical events)
- If query asks for "rule query", "rule SQL", "rule logic", "rule definition" → CURRENT_DATA (rule evaluation logic)
- If query asks for "rule violation" but means the rule's SQL/logic → CURRENT_DATA (rule definition)
- If query asks for "rule violation" but means what happened → HISTORICAL_DATA (violation events)
- If query asks "which rules are violated" or "show violated rules" → CURRENT_DATA (current status)
- If query asks "give me rules that are currently violated" → CURRENT_DATA (current status)

User Query: "{user_query}"

IMPORTANT EXAMPLES:
- "Which rules are violated?" → CURRENT_DATA (current status)
- "Give me the rules that are currently violated" → CURRENT_DATA (current status)
- "Show me violated rules" → CURRENT_DATA (current status)
- "What rules are currently active?" → CURRENT_DATA (current status)
- "Show me rule logic for rule X" → CURRENT_DATA (current definition)
- "What actions happen when rule X violates?" → CURRENT_DATA (current actions)
- "What actions are available?" → CURRENT_DATA (available action types)
- "Show me all action types" → CURRENT_DATA (available action types)
- "Rules whose actions are EMAIL" → CURRENT_DATA (current action configuration)
- "List all rules which has actions as EMAIL" → CURRENT_DATA (current action configuration)
- "Give me a List of all rules whose actions are 'SEND_EMAIL'" → CURRENT_DATA (current action configuration)
- "Give me the Query for the rule violation for rule X" → CURRENT_DATA (rule SQL/logic definition)
- "Show me rule SQL for rule X" → CURRENT_DATA (rule SQL/logic definition)
- "What is the rule logic for rule X" → CURRENT_DATA (rule SQL/logic definition)
- "Rule violation history" → HISTORICAL_DATA (historical data)
- "Events for Channel EMAIL" → HISTORICAL_DATA (historical channel events)
- "SLACK notifications" → HISTORICAL_DATA (historical channel events)
- "What happened when rule X violated?" → HISTORICAL_DATA (historical events)
- "Show me events for Channel EMAIL" → HISTORICAL_DATA (historical channel events)
- "Show me current rule status" → CURRENT_DATA (current data)
- "What is the rule definition?" → CURRENT_DATA (current data)
- "How are rules configured?" → CURRENT_DATA (current data)

Respond with EXACTLY one of these options:
CURRENT_DATA
HISTORICAL_DATA

Data type:"""

    print(f"📝 Data type classification prompt created, length: {len(prompt)} characters")
    print(f"🚀 Sending data type classification request to Ollama...")
    
    data_type = await ollama_client.classify_intent(prompt)
    
    if not data_type:
        print("⚠️ LLM returned empty response for data type classification")
        raise ValueError("LLM returned empty response for data type classification")
    
    return _normalize_data_type_choice(data_type, ["CURRENT_DATA", "HISTORICAL_DATA"])


async def _classify_current_data_tables(user_query: str, ollama_client: OllamaClient) -> str:
    """Level 3: Classify which CURRENT_DATA table to use or if analytics is needed."""
    prompt = f"""
You are a table classifier for CURRENT_DATA within the RULES_GROUP. Based on the user's query, determine which table to use:

CURRENT_DATA TABLES:

MONITOR_RULES: Use for queries about current rule status and basic rule information
- Current rule status (violated, active, enabled)
- Basic rule configuration and settings
- Examples: "show rules", "violated rules", "rule status", "active rules", "enabled rules"

RULES_DEFINITIONS: Use for queries about rule evaluation logic and SQL definitions
- Actual SQL queries that evaluate rule violations
- Rule logic and evaluation criteria
- Examples: "rule logic", "rule SQL", "rule evaluation", "rule definition"

RULES_ACTIONS: Use for queries about actions taken when rules are violated
- Actions configured for rule violations
- Response configurations and settings
- Examples: "rule actions", "what happens when rule violates", "rule responses"

ACTION_EXECUTORS: Use for queries about available action types and executors in the system
- Available action types the system can perform
- Action executor configurations and settings
- Examples: "available actions", "action types", "action executors", "what actions can be performed", "show me all actions"

ANALYTICS: Use for complex queries that require joins or aggregations across CURRENT_DATA tables
- Queries with "most", "highest", "average", "count", "group by"
- Analyzing current rule patterns or configurations
- Examples: "which rules are most configured", "rule configuration patterns", "current rule statistics"

User Query: "{user_query}"

IMPORTANT EXAMPLES:
- "Show me all rules" → MONITOR_RULES
- "Which rules are violated?" → MONITOR_RULES
- "Show me rule logic for rule X" → RULES_DEFINITIONS
- "What actions happen when rule X violates?" → RULES_ACTIONS
- "How are rules configured?" → MONITOR_RULES
- "What actions are available?" → ACTION_EXECUTORS
- "Show me all action types" → ACTION_EXECUTORS
- "Available action executors" → ACTION_EXECUTORS
- "Which rules have the most conditions?" → ANALYTICS
- "Rule configuration patterns" → ANALYTICS

Respond with EXACTLY one of these options:
MONITOR_RULES
RULES_DEFINITIONS
RULES_ACTIONS
ACTION_EXECUTORS
ANALYTICS

Table choice:"""

    print(f"📝 Current data table classification prompt created, length: {len(prompt)} characters")
    print(f"🚀 Sending current data table classification request to Ollama...")
    
    table_choice = await ollama_client.classify_intent(prompt)
    
    if not table_choice:
        print("⚠️ LLM returned empty response for current data table classification")
        raise ValueError("LLM returned empty response for current data table classification")
    
    return _normalize_table_choice(table_choice, ["MONITOR_RULES", "RULES_DEFINITIONS", "RULES_ACTIONS", "ACTION_EXECUTORS", "ANALYTICS"])


async def _classify_historical_data_tables(user_query: str, ollama_client: OllamaClient) -> str:
    """Level 3: Classify which HISTORICAL_DATA table to use or if analytics is needed."""
    prompt = f"""
You are a table classifier for HISTORICAL_DATA within the RULES_GROUP. Based on the user's query, determine which table to use:

HISTORICAL_DATA TABLES:

MONITOR_RULES_LOGS: Use for queries about historical rule evaluation results and channel events
- Rule violation history and audit trails
- Past rule evaluations and results
- Channel-specific events and notifications (EMAIL, SLACK, SMS, PAGERDUTY, OPSGENIE)
- Examples: "rule history", "violation logs", "rule audit trail", "past violations", "EMAIL events", "SLACK notifications", "channel events", "events for Channel EMAIL"

ANALYTICS: Use for complex queries that require analysis of historical data
- Queries with "most", "highest", "average", "count", "group by", "trends"
- Analyzing historical patterns in rule violations or channel events
- Examples: "which rules were violated most last month", "trend of EMAIL notifications over time", "channel usage statistics"

User Query: "{user_query}"

IMPORTANT EXAMPLES:
- "Rule violation history" → MONITOR_RULES_LOGS
- "Events for Channel EMAIL" → MONITOR_RULES_LOGS
- "SLACK notifications" → MONITOR_RULES_LOGS
- "Channel events" → MONITOR_RULES_LOGS
- "Rules with EMAIL actions" → MONITOR_RULES_LOGS
- "Which rules were violated most last month?" → ANALYTICS
- "Trend of EMAIL notifications over time" → ANALYTICS
- "Channel usage statistics" → ANALYTICS

Respond with EXACTLY one of these options:
MONITOR_RULES_LOGS
ANALYTICS

Table choice:"""

    print(f"📝 Historical data table classification prompt created, length: {len(prompt)} characters")
    print(f"🚀 Sending historical data table classification request to Ollama...")
    
    table_choice = await ollama_client.classify_intent(prompt)
    
    if not table_choice:
        print("⚠️ LLM returned empty response for historical data table classification")
        raise ValueError("LLM returned empty response for historical data table classification")
    
    return _normalize_table_choice(table_choice, ["MONITOR_RULES_LOGS", "ANALYTICS"])


async def _classify_rules_analytics(user_query: str, ollama_client: OllamaClient) -> str:
    """Level 3: Classify which type of analytics to use for complex cross-table queries."""
    prompt = f"""
You are an analytics classifier for the RULES_GROUP. Based on the user's query, determine which analytics approach to use:

ANALYTICS TYPES:

CROSS_TABLE_ANALYTICS: Use for complex queries requiring joins across multiple rules tables
- Queries that need data from MONITOR_RULES, RULES_DEFINITIONS, RULES_ACTIONS, and MONITOR_RULES_LOGS
- Examples: "which rules are violated most and what actions do they have", "rule performance analysis"

TREND_ANALYTICS: Use for time-based analysis and pattern recognition
- Queries with "trends", "over time", "patterns", "seasonal"
- Examples: "violation trends over time", "rule performance patterns", "seasonal rule violations"

AGGREGATION_ANALYTICS: Use for statistical analysis and summaries
- Queries with "most", "highest", "average", "count", "group by"
- Examples: "which rules are violated most", "average violations per rule", "rule statistics"

User Query: "{user_query}"

IMPORTANT EXAMPLES:
- "Which rules are violated most?" → AGGREGATION_ANALYTICS
- "Rule performance analysis" → CROSS_TABLE_ANALYTICS
- "Violation trends over time" → TREND_ANALYTICS
- "Rule statistics" → AGGREGATION_ANALYTICS
- "Which rules are violated most and what actions do they have?" → CROSS_TABLE_ANALYTICS

Respond with EXACTLY one of these options:
CROSS_TABLE_ANALYTICS
TREND_ANALYTICS
AGGREGATION_ANALYTICS

Analytics type:"""

    print(f"📝 Rules analytics classification prompt created, length: {len(prompt)} characters")
    print(f"🚀 Sending rules analytics classification request to Ollama...")
    
    analytics_type = await ollama_client.classify_intent(prompt)
    
    if not analytics_type:
        print("⚠️ LLM returned empty response for rules analytics classification")
        raise ValueError("LLM returned empty response for rules analytics classification")
    
    return _normalize_analytics_choice(analytics_type, ["CROSS_TABLE_ANALYTICS", "TREND_ANALYTICS", "AGGREGATION_ANALYTICS"])


async def _classify_actions_group_tables(user_query: str, ollama_client: OllamaClient) -> str:
    """Classify tables within ACTIONS_GROUP."""
    prompt = f"""
You are a table classifier for the ACTIONS_GROUP. Based on the user's query, determine which table to use:

ACTION_EXECUTORS: Use for queries about available action types and executors
- Available action types the system can perform
- Action configurations and settings
- Examples: "show actions", "available actions", "action types", "action executors"

ANALYTICS: Use for complex queries that require analysis of actions data
- Queries with "most", "highest", "average", "count", "group by"
- Analyzing action patterns or usage
- Examples: "most used actions", "action statistics", "action patterns"

User Query: "{user_query}"

IMPORTANT EXAMPLES:
- "What actions are available?" → ACTION_EXECUTORS
- "Available action executors" → ACTION_EXECUTORS
- "Most used actions" → ANALYTICS
- "Action statistics" → ANALYTICS

Respond with EXACTLY one of these options:
ACTION_EXECUTORS
ANALYTICS

Table choice:"""

    print(f"📝 Prompt created, length: {len(prompt)} characters")
    print(f"🚀 Sending request to Ollama...")
    
    table_choice = await ollama_client.classify_intent(prompt)
    
    if not table_choice:
        print("⚠️ LLM returned empty response")
        # Don't retry for empty responses, throw error
        raise ValueError("LLM returned empty response for table classification")
    
    return _normalize_table_choice(table_choice, ["ACTION_EXECUTORS", "ANALYTICS"])


def _normalize_table_choice(table_choice: str, valid_options: list) -> str:
    """Normalize and validate the table choice from Ollama."""
    if not table_choice:
        print("⚠️ Empty table choice from Ollama")
        raise ValueError("Empty table choice from Ollama")
    
    # Clean and normalize the response
    detected_table = table_choice.strip().upper()
    print(f"🔍 Raw table choice: '{detected_table}'")
    
    # Try to extract just the table if LLM added extra text
    if len(detected_table) > 20:  # If response is too long, try to extract the table
        print("🔍 Response seems long, attempting to extract table...")
        for option in valid_options:
            if option in detected_table:
                detected_table = option
                break
        print(f"🔍 Extracted table: '{detected_table}'")
    
    # Check if it's a valid table
    if detected_table in valid_options:
        print(f"✅ Valid table choice: {detected_table}")
        return detected_table
    else:
        print(f"⚠️ LLM returned invalid table: '{detected_table}'")
        # Don't retry for invalid responses, throw error
        raise ValueError(f"LLM returned invalid table: '{detected_table}'. Expected one of: {valid_options}")


def _normalize_data_type_choice(data_type: str, valid_options: list) -> str:
    """Normalize and validate the data type choice from Ollama."""
    if not data_type:
        print("⚠️ Empty data type choice from Ollama")
        raise ValueError("Empty data type choice from Ollama")
    
    # Clean and normalize the response
    detected_type = data_type.strip().upper()
    print(f"🔍 Raw data type choice: '{detected_type}'")
    
    # Try to extract just the type if LLM added extra text
    if len(detected_type) > 20:  # If response is too long, try to extract the type
        print("🔍 Response seems long, attempting to extract data type...")
        for option in valid_options:
            if option in detected_type:
                detected_type = option
                break
        print(f"🔍 Extracted data type: '{detected_type}'")
    
    # Check if it's a valid type
    if detected_type in valid_options:
        print(f"✅ Valid data type choice: {detected_type}")
        return detected_type
    else:
        print(f"⚠️ LLM returned invalid data type: '{detected_type}'")
        raise ValueError(f"LLM returned invalid data type: '{detected_type}'. Expected one of: {valid_options}")


def _normalize_analytics_choice(analytics_type: str, valid_options: list) -> str:
    """Normalize and validate the analytics choice from Ollama."""
    if not analytics_type:
        print("⚠️ Empty analytics choice from Ollama")
        raise ValueError("Empty analytics choice from Ollama")
    
    # Clean and normalize the response
    detected_type = analytics_type.strip().upper()
    print(f"🔍 Raw analytics choice: '{detected_type}'")
    
    # Try to extract just the type if LLM added extra text
    if len(detected_type) > 20:  # If response is too long, try to extract the type
        print("🔍 Response seems long, attempting to extract analytics type...")
        for option in valid_options:
            if option in detected_type:
                detected_type = option
                break
        print(f"🔍 Extracted analytics type: '{detected_type}'")
    
    # Check if it's a valid type
    if detected_type in valid_options:
        print(f"✅ Valid analytics choice: {detected_type}")
        return detected_type
    else:
        print(f"⚠️ LLM returned invalid analytics choice: '{detected_type}'")
        raise ValueError(f"LLM returned invalid analytics choice: '{detected_type}'. Expected one of: {valid_options}")
