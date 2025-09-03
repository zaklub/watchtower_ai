"""
Dynamic SQL query generator for monitor_conditions table based on user requests
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

IMPORTANT: You are working with POSTGRESQL database. Use PostgreSQL syntax.

Given a user's natural language query, generate appropriate SQL WHERE clause conditions for the monitor_conditions table.

Table schema:
- condition_id: Unique condition identifier
- monitor_id: Foreign key to monitored_feeds.monitor_id
- feed_path_name: Path of the Feed/Event coming in to extract
- condition_operator: The condition to evaluate like "=", "!=", ">", "<"
- comparator: The actual value to evaluate the feed_path_name with
- group_operator: Acts as AND/OR/NOT between conditions if more than 1 condition for one monitor

CRITICAL: You must return a COMPLETE and VALID JSON response. The JSON must be properly closed with all brackets and braces.

Expected JSON format (MUST be complete):
{
    "where_conditions": ["condition1", "condition2"],
    "query_description": "human readable description"
}

Examples:
- "Show me all conditions" → {"where_conditions": [], "query_description": "all monitor conditions"}
- "Get conditions for monitor 123" → {"where_conditions": ["c.monitor_id = 123"], "query_description": "conditions for monitor 123"}
- "Show me active conditions" → {"where_conditions": ["c.condition_operator = '='"], "query_description": "equality conditions"}
- "Find threshold conditions" → {"where_conditions": ["c.condition_operator = '>'"], "query_description": "greater than conditions"}
- "Conditions with AND grouping" → {"where_conditions": ["c.group_operator = 'AND'"], "query_description": "conditions with AND grouping"}
- "Path conditions for API feeds" → {"where_conditions": ["c.feed_path_name ILIKE '%API%'"], "query_description": "conditions for API feed paths"}

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
                            if condition.startswith('c.') or condition.startswith('m.') or condition.startswith('DATE('):
                                conditions.append(condition)
                        
                        print(f"🔧 Extracted conditions: {conditions}")
                        print(f"🔧 Extracted description: {description}")
                        return conditions, description
                    else:
                        print("⚠️ Could not extract conditions or description, using fallback")
                        return fallback_word_matching(user_query)
                
                where_conditions = parsed_response.get('where_conditions', [])
                query_description = parsed_response.get('query_description', 'monitor conditions')
                
                print(f"✅ LLM generated {len(where_conditions)} conditions")
                return where_conditions, query_description
                
            else:
                print("⚠️ No JSON found in LLM response, using fallback")
                return fallback_word_matching(user_query)
                
        except Exception as e:
            print(f"⚠️ Error parsing LLM response: {e}, using fallback")
            return fallback_word_matching(user_query)
            
    except Exception as e:
        print(f"⚠️ Error in SQL generation: {e}, using fallback")
        return fallback_word_matching(user_query)


def fallback_word_matching(user_query: str) -> tuple[list[str], str]:
    """Fallback word matching when LLM fails."""
    print("🔄 Using fallback word matching for monitor conditions")
    query_lower = user_query.lower()
    where_conditions = []
    
    # Monitor ID matching
    if 'monitor' in query_lower and any(char.isdigit() for char in user_query):
        import re
        numbers = re.findall(r'\d+', user_query)
        if numbers:
            monitor_id = numbers[0]
            where_conditions.append(f"c.monitor_id = {monitor_id}")
            query_description = f"conditions for monitor {monitor_id}"
    
    # Active status matching
    elif any(word in query_lower for word in ['active', 'enabled', 'on']):
        where_conditions.append("c.is_active = 'TRUE'")
        query_description = "active monitor conditions"
    
    # Inactive status matching
    elif any(word in query_lower for word in ['inactive', 'disabled', 'off']):
        where_conditions.append("c.is_active = 'FALSE'")
        query_description = "inactive monitor conditions"
    
    # Condition type matching
    elif 'threshold' in query_lower:
        where_conditions.append("c.condition_type = 'THRESHOLD'")
        query_description = "threshold type conditions"
    elif 'pattern' in query_lower:
        where_conditions.append("c.condition_type = 'PATTERN'")
        query_description = "pattern type conditions"
    elif 'range' in query_lower:
        where_conditions.append("c.condition_type = 'RANGE'")
        query_description = "range type conditions"
    
    # Time-based matching
    elif any(word in query_lower for word in ['today', 'today\'s', 'current']):
        where_conditions.append("DATE(c.created_at) = CURRENT_DATE")
        query_description = "conditions created today"
    elif 'yesterday' in query_lower:
        where_conditions.append("DATE(c.created_at) = CURRENT_DATE - INTERVAL '1 day'")
        query_description = "conditions created yesterday"
    elif 'week' in query_lower:
        where_conditions.append("c.created_at >= NOW() - INTERVAL '7 days'")
        query_description = "conditions created in last week"
    
    # Default: show all conditions
    if not where_conditions:
        query_description = "all monitor conditions"
    
    return where_conditions, query_description


@tool
async def query_monitor_conditions_dynamic(user_query: str) -> str:
    """Dynamically query monitor conditions based on natural language."""
    try:
        print(f"🔍 Processing monitor conditions query: '{user_query}'")
        
        # Generate WHERE clause conditions
        where_conditions, query_description = await generate_sql_where_clause(user_query)
        
        # Build the SQL query
        base_query = """
        SELECT
            c.condition_id,
            c.monitor_id,
            m.monitor_system_name as monitor_name,
            c.feed_path_name,
            c.condition_operator,
            c.comparator,
            c.group_operator
        FROM monitor_conditions c
        LEFT JOIN monitored_feeds m ON c.monitor_id = m.monitor_id
        """
        
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
        
        base_query += " ORDER BY c.condition_id LIMIT 100"
        
        print(f"🔍 Generated SQL: {base_query}")
        
        # Execute the query
        db_connection = DatabaseConnection()
        results = db_connection.execute_query(base_query)
        
        print(f"✅ Query executed, found {len(results)} results")
        
        # Format the results
        records = []
        for condition in results:
            records.append({
                "condition_id": str(condition['condition_id']) if condition['condition_id'] is not None else None,
                "monitor_id": float(condition['monitor_id']) if condition['monitor_id'] is not None else None,
                "monitor_name": str(condition['monitor_name']) if condition['monitor_name'] is not None else None,
                "condition_name": str(condition['condition_name']) if condition['condition_name'] is not None else None,
                "condition_type": str(condition['condition_type']) if condition['condition_type'] is not None else None,
                "condition_value": str(condition['condition_value']) if condition['condition_value'] is not None else None,
                "condition_operator": str(condition['condition_operator']) if condition['condition_operator'] is not None else None,
                "is_active": str(condition['is_active']) if condition['is_active'] is not None else None,
                "created_at": str(condition['created_at']) if condition['created_at'] is not None else None,
                "updated_at": str(condition['updated_at']) if condition['updated_at'] is not None else None
            })
        
        # Prepare response data
        response_data = {
            "records": records,
            "query_description": query_description,
            "response_metadata": {
                "total_count": len(records),
                "sql_query": base_query,
                "where_conditions": where_conditions
            }
        }
        
        return json.dumps(response_data, indent=2)
        
    except Exception as e:
        error_msg = f"Error processing monitor conditions query '{user_query}': {str(e)}"
        print(f"❌ {error_msg}")
        return json.dumps({
            "error": error_msg,
            "records": [],
            "query_description": "error occurred"
        }, indent=2)
