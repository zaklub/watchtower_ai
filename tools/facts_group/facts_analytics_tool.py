import json
import re
import asyncio
from decimal import Decimal
from langchain_core.tools import tool

from database.db_connection import DatabaseConnection
from ollama_client.ollama_client import OllamaClient


async def generate_complex_sql(user_query: str) -> tuple[str, str]:
    """Generate complex SQL for facts analytics queries using LLM."""
    try:
        system_prompt = """You are a SQL expert specializing in complex analytics queries for monitoring facts systems.

        IMPORTANT: You are working with POSTGRESQL database. Use PostgreSQL syntax.

        Given a user's natural language query, generate a COMPLEX SQL query that involves joins and aggregations across facts tables.

        Available tables:
        1. monitored_facts (mf) - Actual events and performance data
           - fact_id, monitor_id, start_time, end_time, cummulative_measure, samples
        2. monitored_feeds (m) - Monitor definitions and configuration
           - monitor_id, monitor_system_name, monitor_description, is_enabled

        CRITICAL: You must return a COMPLETE and VALID JSON response. The JSON must be properly closed with all brackets and braces.

        Expected JSON format (MUST be complete):
        {
            "sql_query": "SELECT ... FROM ... JOIN ... WHERE ... GROUP BY ... ORDER BY ...",
            "query_description": "human readable description"
        }

        Examples:
        - "Which monitors have the most events?" → {
            "sql_query": "SELECT m.monitor_system_name, COUNT(mf.fact_id) as event_count FROM monitored_feeds m LEFT JOIN monitored_facts mf ON m.monitor_id = mf.monitor_id GROUP BY m.monitor_id, m.monitor_system_name ORDER BY event_count DESC LIMIT 10",
            "query_description": "monitors ranked by number of events"
          }
        - "Average events per monitor" → {
            "sql_query": "SELECT AVG(event_count) as avg_events FROM (SELECT m.monitor_id, COUNT(mf.fact_id) as event_count FROM monitored_feeds m LEFT JOIN monitored_facts mf ON m.monitor_id = mf.monitor_id GROUP BY m.monitor_id) as monitor_event_counts",
            "query_description": "average number of events per monitor"
          }
        - "Performance trends over time" → {
            "sql_query": "SELECT DATE(mf.start_time) as event_date, AVG(mf.cummulative_measure) as avg_measure, COUNT(*) as event_count FROM monitored_facts mf GROUP BY DATE(mf.start_time) ORDER BY event_date DESC LIMIT 30",
            "query_description": "daily performance trends over last 30 days"
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
                    query_description = parsed_response.get('query_description', 'facts analytics query')
                    
                    if sql_query:
                        print(f"✅ LLM generated complex SQL successfully")
                        return sql_query, query_description
                    else:
                        print("⚠️ No SQL query found in LLM response")
                        return _generate_fallback_sql(user_query), "facts analytics query (fallback)"
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON parsing failed: {e}")
                    return _generate_fallback_sql(user_query), "facts analytics query (fallback)"
            else:
                print("⚠️ No JSON found in LLM response")
                return _generate_fallback_sql(user_query), "facts analytics query (fallback)"
        else:
            print("⚠️ Empty response from LLM")
            return _generate_fallback_sql(user_query), "facts analytics query (fallback)"
            
    except Exception as e:
        print(f"⚠️ Error in SQL generation: {e}")
        return _generate_fallback_sql(user_query), "facts analytics query (fallback)"


def _generate_fallback_sql(user_query: str) -> str:
    """Generate fallback SQL when LLM fails."""
    query_lower = user_query.lower()
    
    if "most events" in query_lower or "most facts" in query_lower:
        return """
        SELECT m.monitor_system_name, COUNT(mf.fact_id) as event_count 
        FROM monitored_feeds m 
        LEFT JOIN monitored_facts mf ON m.monitor_id = mf.monitor_id 
        GROUP BY m.monitor_id, m.monitor_system_name 
        ORDER BY event_count DESC 
        LIMIT 10
        """
    elif "average" in query_lower or "avg" in query_lower:
        return """
        SELECT AVG(event_count) as avg_events 
        FROM (
            SELECT m.monitor_id, COUNT(mf.fact_id) as event_count 
            FROM monitored_feeds m 
            LEFT JOIN monitored_facts mf ON m.monitor_id = mf.monitor_id 
        GROUP BY m.monitor_id
        ) as monitor_event_counts
        """
    elif "trends" in query_lower or "time" in query_lower:
        return """
        SELECT DATE(mf.start_time) as event_date, 
               AVG(mf.cummulative_measure) as avg_measure, 
               COUNT(*) as event_count 
        FROM monitored_facts mf 
        GROUP BY DATE(mf.start_time) 
        ORDER BY event_date DESC 
        LIMIT 30
        """
    else:
        # Default: show recent facts
        return """
        SELECT m.monitor_system_name, 
               mf.start_time, 
               mf.end_time, 
               mf.cummulative_measure, 
               mf.samples
        FROM monitored_facts mf
        LEFT JOIN monitored_feeds m ON mf.monitor_id = m.monitor_id
        ORDER BY mf.start_time DESC
        LIMIT 100
        """


@tool
async def execute_facts_analytics_query(user_query: str) -> str:
    """Execute complex analytics queries for the FACTS_GROUP."""
    try:
        print(f"🧠 Processing facts analytics query: '{user_query}'")
        
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
        error_msg = f"Error executing facts analytics query '{user_query}': {str(e)}"
        print(f"❌ {error_msg}")
        return json.dumps({
            "type": "error",
            "error": error_msg,
            "generated_sql": sql_query if 'sql_query' in locals() else "N/A"
        }, indent=2, default=str)
