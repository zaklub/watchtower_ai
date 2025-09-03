"""
Monitor Group Analytics Tool
Handles complex queries involving joins and aggregations across monitor tables
"""

import json
import asyncio
import time
from typing import Optional, Tuple
from decimal import Decimal
from langchain_core.tools import tool

from database.db_connection import DatabaseConnection
from ollama_client.ollama_client import OllamaClient


async def query_monitor_analytics_dynamic(user_query: str) -> list:
    """Dynamic monitor analytics query using LLM for SQL generation."""
    print(f"🧠 Executing monitor analytics tool for: '{user_query}'")
    
    try:
        # Try complex SQL generation first
        sql_query, query_description = await _generate_complex_sql_with_retry(user_query)
        
        if sql_query:
            print(f"🔍 Generated SQL: {sql_query}")
            
            # Execute the query
            db_connection = DatabaseConnection()
            results = await db_connection.execute_query(sql_query)
            
            print(f"✅ Query executed successfully, returned {len(results)} rows")
            return results
        else:
            print("❌ No SQL generated, returning empty result")
            return []
            
    except Exception as e:
        print(f"❌ Error executing monitor analytics query '{user_query}': {e}")
        raise


async def _generate_complex_sql_with_retry(user_query: str) -> Tuple[str, str]:
    """Generate complex SQL with retry logic for Ollama connection failures."""
    print(f"🤖 Starting complex SQL generation for query: '{user_query}'")
    
    max_retries = 3
    retry_delay = 1  # seconds
    start_time = time.time()
    
    for attempt in range(max_retries):
        attempt_start = time.time()
        print(f"\n🔄 === OLLAMA SQL GENERATION ATTEMPT {attempt + 1}/{max_retries} ===")
        print(f"⏱️  Attempt started at: {time.strftime('%H:%M:%S')}")
        
        try:
            print(f"🔌 Initializing Ollama client...")
            ollama_client = OllamaClient()
            print(f"✅ Ollama client initialized successfully")
            
            system_prompt = """You are an expert SQL generator for a monitoring system database. Generate SQL queries based on user requests.

Available tables:
- monitored_feeds (m): monitor_id, monitor_system_name, is_enabled, monitor_type
- monitor_conditions (c): condition_id, monitor_id, condition_operator, group_operator, is_active, condition_value

Generate a JSON response with:
1. sql_query: The complete SQL query
2. query_description: Brief description of what the query does

Example response format:
{
  "sql_query": "SELECT m.monitor_system_name, COUNT(c.condition_id) as total_conditions FROM monitored_feeds m LEFT JOIN monitor_conditions c ON m.monitor_id = c.monitor_id GROUP BY m.monitor_id, m.monitor_system_name ORDER BY total_conditions DESC",
  "query_description": "monitor statistics showing conditions by operator type"
}

Remember: Your response must be a COMPLETE JSON object. No partial responses.

User query: """

            full_prompt = system_prompt + user_query
            print(f"📝 Prompt created, length: {len(full_prompt)} characters")
            print(f"🚀 Sending request to Ollama...")
            
            llm_response = await ollama_client.classify_intent(full_prompt)
            
            if not llm_response:
                print("⚠️ LLM returned empty response")
                # Don't retry for empty responses, throw error
                raise ValueError("LLM returned empty response for SQL generation")
            
            # Process the response
            response_text = llm_response.strip()
            print(f"🔍 Raw LLM response: '{response_text}'")
            
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
                    sql_query = parsed_response.get('sql_query', '')
                    query_description = parsed_response.get('query_description', 'monitor analytics')
                    
                    if sql_query:
                        attempt_duration = time.time() - attempt_start
                        total_duration = time.time() - start_time
                        print(f"🎯 SUCCESS: LLM generated complex SQL successfully")
                        print(f"⏱️  Attempt {attempt + 1} duration: {attempt_duration:.2f}s")
                        print(f"⏱️  Total time: {total_duration:.2f}s")
                        return sql_query, query_description
                    else:
                        print("⚠️ LLM response missing SQL query")
                        # Don't retry for invalid responses, throw error
                        raise ValueError("LLM response missing SQL query")
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ Could not parse LLM JSON response: {e}")
                    # Don't retry for parsing errors, throw error
                    raise ValueError(f"Could not parse LLM JSON response: {e}")
            else:
                print("⚠️ No JSON found in LLM response")
                # Don't retry for invalid responses, throw error
                raise ValueError("No JSON found in LLM response")
                
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


async def _generate_complex_sql(user_query: str) -> Tuple[str, str]:
    """Generate complex SQL using LLM (legacy function - use _generate_complex_sql_with_retry instead)."""
    print("⚠️ Using legacy SQL generation function - this should not be called")
    return await _generate_complex_sql_with_retry(user_query)


@tool
async def execute_monitor_analytics_query(user_query: str) -> str:
    """Execute complex analytics queries for monitor group."""
    try:
        print(f"🧠 Processing monitor analytics query: '{user_query}'")
        
        # Generate complex SQL
        sql_query, query_description = await generate_complex_sql(user_query)
        
        print(f"🔍 Generated SQL: {sql_query}")
        
        # Execute the query
        db_connection = DatabaseConnection()
        results = db_connection.execute_query(sql_query)
        
        print(f"✅ Query executed, found {len(results)} results")
        
        # Format the results with proper JSON serialization
        records = []
        for result in results:
            record = {}
            for key, value in result.items():
                if isinstance(value, Decimal):
                    record[key] = float(value)
                elif hasattr(value, 'isoformat'):  # Handle date, datetime objects
                    record[key] = value.isoformat()
                elif hasattr(value, 'strftime'):  # Handle date objects
                    record[key] = str(value)
                else:
                    record[key] = value
            records.append(record)
        
        # Prepare response data
        response_data = {
            "records": records,
            "query_description": query_description,
            "sql_query": sql_query,
            "response_metadata": {
                "total_count": len(records),
                "query_type": "monitor_analytics",
                "tables_involved": ["monitored_feeds", "monitor_conditions"]
            }
        }
        
        return json.dumps(response_data, indent=2, default=str)
        
    except Exception as e:
        error_msg = f"Error executing monitor analytics query '{user_query}': {str(e)}"
        print(f"❌ {error_msg}")
        return json.dumps({
            "error": error_msg,
            "records": [],
            "query_description": "error occurred",
            "sql_query": sql_query if 'sql_query' in locals() else "N/A"
        }, indent=2, default=str)
