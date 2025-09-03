"""
Dynamic SQL query generator for action_executors table based on user requests
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
        
        system_prompt = """You are a SQL expert specializing in database queries for monitoring and action systems.

IMPORTANT: You are working with POSTGRESQL database. Use PostgreSQL syntax.

Given a user's natural language query, generate appropriate SQL WHERE clause conditions for the action_executors table.

Table schema:
- executor_id: Unique executor identifier (numeric)
- executor_name: Definition of the action which can be used in a Rule (character)
  Available values: "OPSGENIE_TICKET", "SLACK_MESSAGE", "TEAMS_MESSAGE", "PAGERDUTY_TICKET", "OPSGENIE_ALERTS", "SEND_EMAIL", "SEND_TICKET"

CRITICAL: You must return a COMPLETE and VALID JSON response. The JSON must be properly closed with all brackets and braces.

Expected JSON format (MUST be complete):
{
    "where_conditions": ["condition1", "condition2"],
    "query_description": "human readable description"
}

Examples:
- "Show me all action executors" → {"where_conditions": [], "query_description": "all action executors"}
- "Get email executors" → {"where_conditions": ["e.executor_name ILIKE '%EMAIL%'"], "query_description": "email action executors"}
- "Find webhook executors" → {"where_conditions": ["e.executor_name ILIKE '%WEBHOOK%'"], "query_description": "webhook action executors"}
- "What actions are available?" → {"where_conditions": [], "query_description": "available action executors"}
- "Available action executors" → {"where_conditions": [], "query_description": "available action executors"}
- "Show me SLACK actions" → {"where_conditions": ["e.executor_name ILIKE '%SLACK%'"], "query_description": "SLACK action executors"}
- "Find PAGERDUTY executors" → {"where_conditions": ["e.executor_name ILIKE '%PAGERDUTY%'"], "query_description": "PAGERDUTY action executors"}

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
                            if condition.startswith('e.') or condition.startswith('DATE('):
                                conditions.append(condition)
                        
                        print(f"🔧 Extracted conditions: {conditions}")
                        print(f"🔧 Extracted description: {description}")
                        return conditions, description
                    else:
                        print("⚠️ Could not extract conditions or description, using fallback")
                        return fallback_word_matching(user_query)
                
                where_conditions = parsed_response.get('where_conditions', [])
                query_description = parsed_response.get('query_description', 'action executors')
                
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
    print("🔄 Using fallback word matching for action executors")
    query_lower = user_query.lower()
    where_conditions = []
    
    # Action type matching
    if 'email' in query_lower:
        where_conditions.append("e.executor_name ILIKE '%EMAIL%'")
        query_description = "email action executors"
    elif 'slack' in query_lower:
        where_conditions.append("e.executor_name ILIKE '%SLACK%'")
        query_description = "SLACK action executors"
    elif 'sms' in query_lower:
        where_conditions.append("e.executor_name ILIKE '%SMS%'")
        query_description = "SMS action executors"
    elif 'pagerduty' in query_lower:
        where_conditions.append("e.executor_name ILIKE '%PAGERDUTY%'")
        query_description = "PagerDuty action executors"
    elif 'opsgenie' in query_lower:
        where_conditions.append("e.executor_name ILIKE '%OPSGENIE%'")
        query_description = "OpsGenie action executors"
    elif 'webhook' in query_lower:
        where_conditions.append("e.executor_name ILIKE '%WEBHOOK%'")
        query_description = "webhook action executors"
    
    # Default: show all action executors
    if not where_conditions:
        query_description = "all action executors"
    
    return where_conditions, query_description


@tool
async def query_action_executors_dynamic(user_query: str) -> str:
    """Dynamically query action executors based on natural language."""
    try:
        print(f"🔍 Processing action executors query: '{user_query}'")
        
        # Generate WHERE clause conditions
        where_conditions, query_description = await generate_sql_where_clause(user_query)
        
        # Build the SQL query
        base_query = """
        SELECT
            e.executor_id,
            e.executor_name
        FROM action_executors e
        """
        
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
        
        base_query += " ORDER BY e.executor_id LIMIT 100"
        
        print(f"🔍 Generated SQL: {base_query}")
        
        # Execute the query
        db_connection = DatabaseConnection()
        results = db_connection.execute_query(base_query)
        
        print(f"✅ Query executed, found {len(results)} results")
        
        # Format the results
        records = []
        for executor in results:
            records.append({
                "executor_id": str(executor['executor_id']) if executor['executor_id'] is not None else None,
                "executor_name": str(executor['executor_name']) if executor['executor_name'] is not None else None
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
        error_msg = f"Error processing action executors query '{user_query}': {str(e)}"
        print(f"❌ {error_msg}")
        return json.dumps({
            "error": error_msg,
            "records": [],
            "query_description": "error occurred"
        }, indent=2)
