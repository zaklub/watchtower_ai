import json
import re
import asyncio
from decimal import Decimal
from langchain_core.tools import tool

from database.db_connection import DatabaseConnection
from ollama_client.ollama_client import OllamaClient


async def generate_complex_sql(user_query: str) -> tuple[str, str]:
    """Generate complex SQL for actions analytics queries using LLM."""
    try:
        system_prompt = """You are a SQL expert specializing in complex analytics queries for monitoring action systems.

        IMPORTANT: You are working with POSTGRESQL database. Use PostgreSQL syntax.

        Given a user's natural language query, generate a COMPLEX SQL query that involves joins and aggregations across action tables.

        Available tables:
        1. action_executors (ae) - Action executor definitions
           - executor_id, executor_name, configs
        2. rule_actions (ra) - Actions configured for rules
           - action_id, rules_id, executor_id, is_active
        3. monitor_rules (r) - Rule definitions and status
           - rule_id, rule_name, monitor_id, is_violated, is_active

        CRITICAL: You must return a COMPLETE and VALID JSON response. The JSON must be properly closed with all brackets and braces.

        Expected JSON format (MUST be complete):
        {
            "sql_query": "SELECT ... FROM ... JOIN ... WHERE ... GROUP BY ... ORDER BY ...",
            "query_description": "human readable description"
        }

        Examples:
        - "Most used actions" → {
            "sql_query": "SELECT ae.executor_name, COUNT(ra.action_id) as usage_count FROM action_executors ae LEFT JOIN rule_actions ra ON ae.executor_id = ra.executor_id WHERE ra.is_active = 'TRUE' GROUP BY ae.executor_id, ae.executor_name ORDER BY usage_count DESC LIMIT 10",
            "query_description": "action executors ranked by usage frequency"
          }
        - "Actions by rule type" → {
            "sql_query": "SELECT r.rule_name, ae.executor_name, COUNT(ra.action_id) as action_count FROM monitor_rules r LEFT JOIN rule_actions ra ON r.rule_id = ra.rules_id LEFT JOIN action_executors ae ON ra.executor_id = ae.executor_id GROUP BY r.rule_id, r.rule_name, ae.executor_id, ae.executor_name ORDER BY action_count DESC",
            "query_description": "actions grouped by rule type"
          }
        - "Active action statistics" → {
            "sql_query": "SELECT ae.executor_name, SUM(CASE WHEN ra.is_active = 'TRUE' THEN 1 ELSE 0 END) as active_actions, COUNT(ra.action_id) as total_actions FROM action_executors ae LEFT JOIN rule_actions ra ON ae.executor_id = ra.executor_id GROUP BY ae.executor_id, ae.executor_name ORDER BY total_actions DESC",
            "query_description": "action statistics showing active vs total actions"
          }

        Remember: Your response must be a COMPLETE JSON object. No partial responses.

        User query: """

        ollama_client = OllamaClient()
        prompt = f"{system_prompt}\n\n{user_query}"
        
        print(f"🤖 Sending query to LLM for complex SQL generation: '{user_query}'")
        response = await ollama_client.query(prompt)
        
        if response and response.strip():
            print(f"✅ LLM raw response: {response}")
            
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}')
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end + 1]
                json_str = json_str.strip()
                
                # Handle common LLM formatting issues
                json_str = json_str.replace('\n', ' ').replace('\r', ' ')
                json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
                json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays
                
                try:
                    parsed_response = json.loads(json_str)
                    sql_query = parsed_response.get('sql_query', '')
                    query_description = parsed_response.get('query_description', 'actions analytics query')
                    
                    if sql_query:
                        print(f"✅ LLM generated complex SQL successfully")
                        return sql_query, query_description
                    else:
                        print("⚠️ No SQL query found in LLM response")
                        return _generate_fallback_sql(user_query), "actions analytics query (fallback)"
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON parsing failed: {e}")
                    return _generate_fallback_sql(user_query), "actions analytics query (fallback)"
            else:
                print("⚠️ No JSON found in LLM response")
                return _generate_fallback_sql(user_query), "actions analytics query (fallback)"
        else:
            print("⚠️ Empty response from LLM")
            return _generate_fallback_sql(user_query), "actions analytics query (fallback)"
            
    except Exception as e:
        print(f"⚠️ Error in SQL generation: {e}")
        return _generate_fallback_sql(user_query), "actions analytics query (fallback)"


def _generate_fallback_sql(user_query: str) -> str:
    """Generate fallback SQL when LLM fails."""
    query_lower = user_query.lower()
    
    if "most used" in query_lower or "usage" in query_lower:
        return """
        SELECT ae.executor_name, COUNT(ra.action_id) as usage_count 
        FROM action_executors ae 
        LEFT JOIN rule_actions ra ON ae.executor_id = ra.executor_id 
        WHERE ra.is_active = 'TRUE' 
        GROUP BY ae.executor_id, ae.executor_name 
        ORDER BY usage_count DESC 
        LIMIT 10
        """
    elif "by rule" in query_lower or "rule type" in query_lower:
        return """
        SELECT r.rule_name, ae.executor_name, COUNT(ra.action_id) as action_count 
        FROM monitor_rules r 
        LEFT JOIN rule_actions ra ON r.rule_id = ra.rules_id 
        LEFT JOIN action_executors ae ON ra.executor_id = ae.executor_id 
        GROUP BY r.rule_id, r.rule_name, ae.executor_id, ae.executor_name 
        ORDER BY action_count DESC
        """
    elif "statistics" in query_lower or "stats" in query_lower:
        return """
        SELECT ae.executor_name, 
               SUM(CASE WHEN ra.is_active = 'TRUE' THEN 1 ELSE 0 END) as active_actions, 
               COUNT(ra.action_id) as total_actions 
        FROM action_executors ae 
        LEFT JOIN rule_actions ra ON ae.executor_id = ra.executor_id 
        GROUP BY ae.executor_id, ae.executor_name 
        ORDER BY total_actions DESC
        """
    else:
        # Default: show action usage summary
        return """
        SELECT ae.executor_name, 
               COUNT(ra.action_id) as total_actions,
               SUM(CASE WHEN ra.is_active = 'TRUE' THEN 1 ELSE 0 END) as active_actions
        FROM action_executors ae
        LEFT JOIN rule_actions ra ON ae.executor_id = ra.executor_id
        GROUP BY ae.executor_id, ae.executor_name
        ORDER BY total_actions DESC
        LIMIT 100
        """


@tool
async def execute_actions_analytics_query(user_query: str) -> str:
    """Execute complex analytics queries for the ACTIONS_GROUP."""
    try:
        print(f"🧠 Processing actions analytics query: '{user_query}'")
        
        # Generate complex SQL
        sql_query, query_description = await generate_complex_sql(user_query)
        
        print(f"🔍 Generated SQL: {sql_query}")
        
        # Execute the query
        db_connection = DatabaseConnection()
        results = db_connection.execute_query(sql_query)
        
        if results:
            print(f"✅ Query executed successfully, returned {len(results)} rows")
            
            # Format response
            response_data = {
                "type": "analytics",
                "query_description": query_description,
                "generated_sql": sql_query,
                "results": results,
                "row_count": len(results)
            }
            
            return json.dumps(response_data, indent=2, default=str)
        else:
            print("✅ Query executed successfully, returned 0 rows")
            return json.dumps({
                "type": "analytics",
                "query_description": query_description,
                "generated_sql": sql_query,
                "results": [],
                "row_count": 0,
                "message": "No data found for this query"
            }, indent=2, default=str)
            
    except Exception as e:
        error_msg = f"Error executing actions analytics query '{user_query}': {str(e)}"
        print(f"❌ {error_msg}")
        return json.dumps({
            "type": "error",
            "error": error_msg,
            "generated_sql": sql_query if 'sql_query' in locals() else "N/A"
        }, indent=2, default=str)
