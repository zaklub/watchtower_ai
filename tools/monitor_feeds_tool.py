"""
Dynamic SQL query generator for monitored_feeds table based on user requests
"""

import json
import asyncio
from decimal import Decimal
from langchain_core.tools import tool

from database.db_connection import DatabaseConnection
from ollama_client.ollama_client import OllamaClient


async def generate_sql_where_clause(user_query: str) -> tuple[list[str], str]:
    """Use LLM to dynamically generate SQL WHERE clause conditions based on natural language query."""
    try:
        ollama_client = OllamaClient()
        
        system_prompt = """You are a SQL expert specializing in database queries for monitoring and configuration systems.

Given a user's natural language query, generate appropriate SQL WHERE clause conditions for the monitored_feeds table.

Table schema:
- monitor_id: Unique monitor identifier (Primary Key)
- monitor_system_name: Name of the Monitor
- monitor_description: Description of the Monitor
- measure_transaction: TRUE = store sum of details, FALSE = store count of events
- measure_field_path: Path to be utilized to calculate the measure
- is_enabled: Whether the monitor is enabled or not

CRITICAL: You must return a COMPLETE and VALID JSON response. The JSON must be properly closed with all brackets and braces.

Expected JSON format (MUST be complete):
{
    "where_conditions": ["condition1", "condition2"],
    "query_description": "human readable description"
}

Examples:
- "Show me all monitors" → {"where_conditions": [], "query_description": "all monitors"}
- "Get enabled monitors" → {"where_conditions": ["is_enabled = 'TRUE'"], "query_description": "enabled monitors"}
- "Find monitors for transaction counting" → {"where_conditions": ["measure_transaction = 'FALSE'"], "query_description": "monitors for event counting"}
- "Show monitors for sum calculation" → {"where_conditions": ["measure_transaction = 'TRUE'"], "query_description": "monitors for sum calculation"}
- "Find monitor by name 'CPU Usage'" → {"where_conditions": ["monitor_system_name ILIKE '%CPU Usage%'"], "query_description": "monitors with name containing 'CPU Usage'"}
- "Get disabled monitors" → {"where_conditions": ["is_enabled = 'FALSE'"], "query_description": "disabled monitors"}
- "Show monitor details for ID 123" → {"where_conditions": ["monitor_id = 123"], "query_description": "monitor with ID 123"}
- "Find monitors for SAP systems" → {"where_conditions": ["monitor_system_name ILIKE '%SAP%'"], "query_description": "monitors for SAP systems"}
- "Get monitors that count events and are enabled" → {"where_conditions": ["measure_transaction = 'FALSE'", "is_enabled = 'TRUE'"], "query_description": "enabled event counting monitors"}
- "Show monitors with descriptions" → {"where_conditions": ["monitor_description IS NOT NULL AND monitor_description != ''"], "query_description": "monitors with descriptions"}

Remember: Your response must be a COMPLETE JSON object. No partial responses.

User query: """

        full_prompt = system_prompt + user_query
        
        print(f"🤖 Sending query to LLM for SQL generation: '{user_query}'")
        
        llm_response = await ollama_client.classify_intent(full_prompt)
        
        if not llm_response:
            print("⚠️ LLM failed to respond, using fallback word matching")
            return fallback_word_matching(user_query)
        
        try:
            response_text = llm_response.strip()
            
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                print(f"🔍 Extracted JSON: {json_str}")
                
                if not json_str.strip().endswith('}'):
                    json_str += '}'
                    print(f"🔧 Fixed incomplete JSON: {json_str}")
                
                try:
                    parsed_response = json.loads(json_str)
                except json.JSONDecodeError:
                    print("🔧 Attempting to extract where_conditions from incomplete JSON...")
                    conditions_match = re.search(r'"where_conditions":\s*\[(.*?)\]', json_str, re.DOTALL)
                    description_match = re.search(r'"query_description":\s*"([^"]*)"', json_str)
                    
                    if conditions_match and description_match:
                        conditions_str = conditions_match.group(1)
                        description = description_match.group(1)
                        
                        conditions = []
                        condition_matches = re.findall(r'"([^"]*)"', conditions_str)
                        for condition in condition_matches:
                            if condition.startswith('is_') or condition.startswith('monitor_') or condition.startswith('measure_'):
                                conditions.append(condition)
                        
                        if conditions:
                            print(f"🔧 Manually extracted conditions: {conditions}")
                            print(f"🔧 Manually extracted description: {description}")
                            return conditions, description
                    
                    raise Exception("Could not extract valid conditions from incomplete JSON")
            else:
                parsed_response = json.loads(response_text)
            
            where_conditions = parsed_response.get("where_conditions", [])
            query_description = parsed_response.get("query_description", "monitors based on LLM analysis")
            
            print(f"✅ LLM generated WHERE conditions: {where_conditions}")
            print(f"✅ LLM generated description: {query_description}")
            
            return where_conditions, query_description
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse LLM response as JSON: {e}")
            print(f"❌ Raw LLM response: {llm_response}")
            print("⚠️ Falling back to word-matching logic due to JSON parsing failure...")
            return fallback_word_matching(user_query)
            
    except Exception as e:
        print(f"❌ Error in LLM-based SQL generation: {e}")
        print("⚠️ Falling back to word-matching logic due to LLM failure...")
        return fallback_word_matching(user_query)


def fallback_word_matching(user_query: str) -> tuple[list[str], str]:
    """Fallback method using word-matching logic when LLM is unavailable."""
    query_lower = user_query.lower()
    where_conditions = []
    query_description = "monitors"
    
    if any(word in query_lower for word in ['enabled', 'active', 'running']):
        where_conditions.append("is_enabled = 'TRUE'")
        query_description = "enabled monitors"
        
    elif any(word in query_lower for word in ['disabled', 'inactive', 'stopped']):
        where_conditions.append("is_enabled = 'FALSE'")
        query_description = "disabled monitors"
        
    elif any(word in query_lower for word in ['transaction', 'sum', 'total', 'addition']):
        where_conditions.append("measure_transaction = 'TRUE'")
        query_description = "monitors for sum calculation"
        
    elif any(word in query_lower for word in ['count', 'counting', 'events', 'occurrence']):
        where_conditions.append("measure_transaction = 'FALSE'")
        query_description = "monitors for event counting"
        
    elif 'monitor' in query_lower and any(char.isdigit() for char in user_query):
        import re
        monitor_ids = re.findall(r'\d+', user_query)
        if monitor_ids:
            monitor_id = monitor_ids[0]
            where_conditions.append(f"monitor_id = {monitor_id}")
            query_description = f"monitor with ID {monitor_id}"
            
    elif any(word in query_lower for word in ['name', 'called', 'named']):
        import re
        quoted_names = re.findall(r'"([^"]+)"', user_query)
        if quoted_names:
            monitor_name = quoted_names[0]
            where_conditions.append(f"monitor_system_name ILIKE '%{monitor_name}%'")
            query_description = f"monitors with name containing '{monitor_name}'"
        else:
            common_names = ['cpu', 'memory', 'disk', 'network', 'database', 'api', 'service', 'sap']
            for name in common_names:
                if name in query_lower:
                    where_conditions.append(f"monitor_system_name ILIKE '%{name}%'")
                    query_description = f"monitors with name containing '{name}'"
                    break
                    
    elif any(word in query_lower for word in ['description', 'described', 'about']):
        where_conditions.append("monitor_description IS NOT NULL AND monitor_description != ''")
        query_description = "monitors with descriptions"
        
    elif any(word in query_lower for word in ['all', 'every', 'total', 'complete', 'entire', 'list']):
        query_description = "all monitors"
        
    else:
        query_description = "all monitors"
    
    return where_conditions, query_description


@tool
async def query_monitor_feeds_dynamic(user_query: str) -> str:
    """Dynamically query the monitored_feeds table based on user's natural language request."""
    
    try:
        print(f"🔍 Dynamic query for monitor feeds: '{user_query}'")
        
        db = DatabaseConnection()
        
        base_query = """
        SELECT
            monitor_id,
            monitor_system_name,
            monitor_description,
            measure_transaction,
            measure_field_path,
            is_enabled
        FROM monitored_feeds
        """
        
        try:
            where_conditions, query_description = await generate_sql_where_clause(user_query)
            print(f"🤖 LLM generated SQL for: {query_description}")
        except Exception as e:
            print(f"❌ LLM-based generation failed: {e}")
            print(f"⚠️ Falling back to word-matching logic...")
            where_conditions, query_description = fallback_word_matching(user_query)
            print(f"🔄 Fallback generated: {query_description}")
        
        order_by = "ORDER BY monitor_id"
        limit_clause = "LIMIT 100"
        
        if where_conditions:
            where_clause = " WHERE " + " AND ".join(where_conditions)
        else:
            where_clause = ""
            
        final_query = f"{base_query}{where_clause} {order_by} {limit_clause}"
        
        print(f"🔍 Generated SQL for {query_description}")
        print(f"🔍 SQL:\n{final_query}")
        
        results = db.execute_query(final_query)
        
        if not results:
            return f"No monitors found for query: {query_description}"
        
        class DecimalEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, Decimal):
                    return float(o)
                return super(DecimalEncoder, self).default(o)
        
        records = []
        
        for monitor in results:
            records.append({
                "monitor_id": int(monitor['monitor_id']) if monitor['monitor_id'] is not None else None,
                "monitor_system_name": str(monitor['monitor_system_name']) if monitor['monitor_system_name'] is not None else None,
                "monitor_description": str(monitor['monitor_description']) if monitor['monitor_description'] is not None else None,
                "measure_transaction": str(monitor['measure_transaction']) if monitor['measure_transaction'] is not None else None,
                "measure_field_path": str(monitor['measure_field_path']) if monitor['measure_field_path'] is not None else None,
                "is_enabled": str(monitor['is_enabled']) if monitor['is_enabled'] is not None else None
            })
        
        # Return enhanced response with records, metadata, and generated SQL
        response_data = {
            "records": records,
            "query_description": query_description,
            "total_count": len(records),
            "sql_query": final_query,  # Include the generated SQL
            "response_metadata": {
                "table_name": "monitored_feeds",
                "query_type": "monitor_configuration",
                "sql_generated": True
            }
        }
        
        return json.dumps(response_data, cls=DecimalEncoder, indent=2)
        
    except Exception as e:
        error_msg = f"Error processing dynamic monitor feeds query '{user_query}': {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg
