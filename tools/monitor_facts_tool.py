"""
Dynamic SQL query generator for monitored_facts table based on user requests
This table stores actual measured values and event counts for monitors over time ranges
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
        
        system_prompt = """You are a SQL expert specializing in database queries for monitoring performance and metrics systems.

IMPORTANT: You are working with POSTGRESQL database. Use PostgreSQL syntax.

Given a user's natural language query, generate appropriate SQL WHERE clause conditions for the monitored_facts table.

Table schema:
- fact_id: Primary key, unique fact identifier (character varying 50)
- monitor_id: Foreign key to monitored_feeds.monitor_id (numeric)
- start_time: Start time of the collection range (timestamp)
- end_time: End time of the collection range (timestamp)
- cummulative_measure: Cumulative count or sum value (numeric)
- samples: Number of samples/events for this monitor (character varying 32)

CRITICAL: You must return a COMPLETE and VALID JSON response. The JSON must be properly closed with all brackets and braces.

Expected JSON format (MUST be complete):
{
    "where_conditions": ["condition1", "condition2"],
    "query_description": "human readable description"
}

Examples:
- "Show me all performance data" → {"where_conditions": [], "query_description": "all performance data"}
- "Get facts from last 24 hours" → {"where_conditions": ["f.start_time >= NOW() - INTERVAL '24 hours'"], "query_description": "performance data from last 24 hours"}
- "Show me high throughput monitors" → {"where_conditions": ["f.cummulative_measure > 1000"], "query_description": "high throughput monitors"}
- "Find facts for monitor 123" → {"where_conditions": ["f.monitor_id = 123"], "query_description": "performance data for monitor 123"}
- "Get data from today" → {"where_conditions": ["DATE(f.start_time) = CURRENT_DATE"], "query_description": "today's performance data"}
- "Show me monitors with more than 100 samples" → {"where_conditions": ["f.samples::numeric > 100"], "query_description": "monitors with high sample counts"}
- "Performance data from last week" → {"where_conditions": ["f.start_time >= NOW() - INTERVAL '7 days'"], "query_description": "performance data from last week"}
- "Monitors with cumulative measure above 5000" → {"where_conditions": ["f.cummulative_measure > 5000"], "query_description": "high performing monitors"}
- "Show me performance data for SAP monitor" → {"where_conditions": ["m.monitor_system_name ILIKE '%SAP%'"], "query_description": "performance data for SAP monitors"}

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
                            if condition.startswith('f.') or condition.startswith('DATE('):
                                conditions.append(condition)
                        
                        if conditions:
                            print(f"🔧 Manually extracted conditions: {conditions}")
                            print(f"🔧 Manually extracted description: {description}")
                            return conditions, description
                    
                    raise Exception("Could not extract valid conditions from incomplete JSON")
            else:
                parsed_response = json.loads(response_text)
            
            where_conditions = parsed_response.get("where_conditions", [])
            query_description = parsed_response.get("query_description", "performance data based on LLM analysis")
            
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
    query_description = "performance data"
    
    if any(word in query_lower for word in ['recent', 'latest', 'last']):
        where_conditions.append("f.start_time >= NOW() - INTERVAL '7 days'")
        query_description = "recent performance data"
        
    elif 'hour' in query_lower:
        if '24' in query_lower or 'day' in query_lower:
            where_conditions.append("f.start_time >= NOW() - INTERVAL '24 hours'")
            query_description = "performance data from last 24 hours"
        else:
            where_conditions.append("f.start_time >= NOW() - INTERVAL '1 hour'")
            query_description = "performance data from last hour"
            
    elif 'week' in query_lower:
        where_conditions.append("f.start_time >= NOW() - INTERVAL '7 days'")
        query_description = "performance data from last week"
        
    elif 'month' in query_lower:
        where_conditions.append("f.start_time >= NOW() - INTERVAL '30 days'")
        query_description = "performance data from last month"
        
    elif 'today' in query_lower:
        where_conditions.append("DATE(f.start_time) = CURRENT_DATE")
        query_description = "today's performance data"
        
    elif 'yesterday' in query_lower:
        where_conditions.append("DATE(f.start_time) = CURRENT_DATE - INTERVAL '1 day'")
        query_description = "yesterday's performance data"
        
    elif any(word in query_lower for word in ['high', 'above', 'more than']):
        # Extract number from query
        import re
        number_match = re.search(r'(\d+)', query_lower)
        threshold = number_match.group(1) if number_match else 1000
        
        if 'sample' in query_lower:
            where_conditions.append(f"f.samples::numeric > {threshold}")
            query_description = f"monitors with more than {threshold} samples"
        else:
            where_conditions.append(f"f.cummulative_measure > {threshold}")
            query_description = f"monitors with cumulative measure above {threshold}"
            
    elif 'monitor' in query_lower and any(char.isdigit() for char in user_query):
        import re
        monitor_ids = re.findall(r'\d+', user_query)
        if monitor_ids:
            monitor_id = monitor_ids[0]
            where_conditions.append(f"f.monitor_id = {monitor_id}")
            query_description = f"performance data for monitor {monitor_id}"
            
    elif any(word in query_lower for word in ['name', 'called', 'named']):
        import re
        quoted_names = re.findall(r'"([^"]+)"', user_query)
        if quoted_names:
            monitor_name = quoted_names[0]
            where_conditions.append(f"m.monitor_system_name ILIKE '%{monitor_name}%'")
            query_description = f"performance data for monitors with name containing '{monitor_name}'"
        else:
            common_names = ['cpu', 'memory', 'disk', 'network', 'database', 'api', 'service', 'sap']
            for name in common_names:
                if name in query_lower:
                    where_conditions.append(f"m.monitor_system_name ILIKE '%{name}%'")
                    query_description = f"performance data for monitors with name containing '{name}'"
                    break
            
    elif any(word in query_lower for word in ['all', 'every', 'total', 'complete', 'entire']):
        query_description = "all performance data"
        
    else:
        query_description = "all performance data"
    
    return where_conditions, query_description


@tool
async def query_monitor_facts_dynamic(user_query: str) -> str:
    """Dynamically query the monitored_facts table based on user's natural language request."""
    
    try:
        print(f"🔍 Dynamic query for monitor facts: '{user_query}'")
        
        db = DatabaseConnection()
        
        base_query = """
        SELECT
            f.fact_id,
            f.monitor_id,
            m.monitor_system_name as monitor_name,  -- Foreign key reference to monitored_feeds.monitor_id
            f.start_time,
            f.end_time,
            f.cummulative_measure,
            f.samples
        FROM monitored_facts f
        LEFT JOIN monitored_feeds m ON f.monitor_id = m.monitor_id  -- Join with monitored_feeds to get monitor name
        """
        
        try:
            where_conditions, query_description = await generate_sql_where_clause(user_query)
            print(f"🤖 LLM generated SQL for: {query_description}")
        except Exception as e:
            print(f"❌ LLM-based generation failed: {e}")
            print(f"⚠️ Falling back to word-matching logic...")
            where_conditions, query_description = fallback_word_matching(user_query)
            print(f"🔄 Fallback generated: {query_description}")
        
        order_by = "ORDER BY f.start_time DESC"
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
            return f"No performance data found for query: {query_description}"
        
        class DecimalEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, Decimal):
                    return float(o)
                return super(DecimalEncoder, self).default(o)
        
        records = []
        
        for fact in results:
            records.append({
                "fact_id": str(fact['fact_id']) if fact['fact_id'] is not None else None,
                "monitor_id": float(fact['monitor_id']) if fact['monitor_id'] is not None else None,
                "monitor_name": str(fact['monitor_name']) if fact['monitor_name'] is not None else None,
                "start_time": str(fact['start_time']) if fact['start_time'] is not None else None,
                "end_time": str(fact['end_time']) if fact['end_time'] is not None else None,
                "cummulative_measure": float(fact['cummulative_measure']) if fact['cummulative_measure'] is not None else None,
                "samples": str(fact['samples']) if fact['samples'] is not None else None
            })
        
        # Return enhanced response with records, metadata, and generated SQL
        response_data = {
            "records": records,
            "query_description": query_description,
            "total_count": len(records),
            "sql_query": final_query,  # Include the generated SQL
            "response_metadata": {
                "table_name": "monitored_facts",
                "query_type": "performance_metrics",
                "sql_generated": True
            }
        }
        
        return json.dumps(response_data, cls=DecimalEncoder, indent=2)
        
    except Exception as e:
        error_msg = f"Error processing dynamic monitor facts query '{user_query}': {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg
