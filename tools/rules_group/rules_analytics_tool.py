"""
Rules Group Analytics Tool
Handles complex queries involving joins and aggregations across rules tables
"""

import json
import asyncio
from decimal import Decimal
from langchain_core.tools import tool

from database.db_connection import DatabaseConnection
from ollama_client.ollama_client import OllamaClient


async def generate_complex_sql(user_query: str) -> tuple[str, str]:
    """Use LLM to generate complex SQL for rules analytics queries."""
    try:
        ollama_client = OllamaClient()
        
        system_prompt = """You are a SQL expert specializing in complex analytics queries for monitoring rules systems.

IMPORTANT: You are working with POSTGRESQL database. Use PostgreSQL syntax.

Given a user's natural language query, generate a COMPLEX SQL query that involves joins and aggregations across rules tables.

Available tables:
1. monitor_rules (r) - Rule definitions and status
   - rule_id, rule_name, monitor_id, is_violated, is_active, is_enabled, created_at
2. rules_definitions (rd) - Rule evaluation logic and SQL
   - definition_id, rule_id, evaluator_id, evaluation_query, use_query, evaluated_measure, evaluation_operator, definition_operator, definition_name
3. rule_actions (ra) - Actions configured for rules
   - action_id, rules_id, executor_id, is_active
4. monitor_rules_logs (mrl) - Rule violation history and logs
   - log_id, rule_id, log_timestamp, audit_type, priority, channel, status
5. monitored_feeds (mf) - Monitor information
   - monitor_id, monitor_system_name, is_enabled

CRITICAL: You must return a COMPLETE and VALID JSON response. The JSON must be properly closed with all brackets and braces.

Expected JSON format (MUST be complete):
{
    "sql_query": "SELECT ... FROM ... JOIN ... WHERE ... GROUP BY ... ORDER BY ...",
    "query_description": "human readable description"
}

Examples:
- "Which rules are violated most?" → {
            "sql_query": "SELECT r.rule_name, COUNT(mrl.log_id) as violation_count FROM monitor_rules r LEFT JOIN monitor_rules_logs mrl ON r.rule_id = mrl.rule_id WHERE mrl.audit_type = 'VIOLATION' GROUP BY r.rule_id, r.rule_name ORDER BY violation_count DESC LIMIT 10",
    "query_description": "rules ranked by violation frequency"
  }
- "Violation trends over time" → {
            "sql_query": "SELECT DATE(mrl.log_timestamp) as violation_date, COUNT(*) as violation_count FROM monitor_rules_logs mrl WHERE mrl.audit_type = 'VIOLATION' GROUP BY DATE(mrl.log_timestamp) ORDER BY violation_date DESC LIMIT 30",
    "query_description": "daily violation trends over last 30 days"
  }
- "Channel notification statistics" → {
    "sql_query": "SELECT mrl.channel, COUNT(*) as notification_count, AVG(CASE WHEN mrl.status = 'SENT' THEN 1 ELSE 0 END) as success_rate FROM monitor_rules_logs mrl WHERE mrl.audit_type = 'NOTIFICATION' GROUP BY mrl.channel ORDER BY notification_count DESC",
    "query_description": "notification statistics by channel"
  }
- "Plot me a chart for Channel EMAIL for last 100 days" → {
    "sql_query": "SELECT DATE(mrl.log_timestamp) as notification_date, COUNT(*) as email_count FROM monitor_rules_logs mrl WHERE mrl.channel = 'EMAIL' AND mrl.log_timestamp >= NOW() - INTERVAL '100 days' GROUP BY DATE(mrl.log_timestamp) ORDER BY notification_date",
    "query_description": "daily EMAIL notifications over last 100 days"
  }

Remember: Your response must be a COMPLETE JSON object. No partial responses.

User query: """

        full_prompt = system_prompt + user_query
        
        print(f"🤖 Sending query to LLM for complex SQL generation: '{user_query}'")
        
        llm_response = await ollama_client.classify_intent(full_prompt)
        
        if not llm_response:
            print("⚠️ LLM failed to respond, using fallback SQL")
            return _generate_fallback_sql(user_query)
        
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
                    sql_query = parsed_response.get('sql_query', '')
                    query_description = parsed_response.get('query_description', 'rules analytics')
                    
                    if sql_query:
                        print(f"✅ LLM generated complex SQL successfully")
                        return sql_query, query_description
                    else:
                        print("⚠️ LLM response missing SQL query, using fallback")
                        return _generate_fallback_sql(user_query)
                        
                except json.JSONDecodeError:
                    print("⚠️ Could not parse LLM JSON response, using fallback")
                    return _generate_fallback_sql(user_query)
            else:
                print("⚠️ No JSON found in LLM response, using fallback")
                return _generate_fallback_sql(user_query)
                
        except Exception as e:
            print(f"⚠️ Error parsing LLM response: {e}, using fallback")
            return _generate_fallback_sql(user_query)
            
    except Exception as e:
        print(f"⚠️ Error in complex SQL generation: {e}, using fallback")
        return _generate_fallback_sql(user_query)


def _generate_fallback_sql(user_query: str) -> tuple[str, str]:
    """Generate fallback SQL when LLM fails."""
    print("🔄 Using fallback SQL generation for rules analytics")
    query_lower = user_query.lower()
    
    # Channel-specific queries
    if 'channel email' in query_lower or 'email' in query_lower:
        if 'last 100 days' in query_lower or '100 days' in query_lower:
            sql = """
            SELECT 
                DATE(mrl.log_timestamp) as notification_date, 
                COUNT(*) as email_count 
            FROM monitor_rules_logs mrl 
            WHERE mrl.channel = 'EMAIL' 
            AND mrl.log_timestamp >= NOW() - INTERVAL '100 days' 
            GROUP BY DATE(mrl.log_timestamp) 
            ORDER BY notification_date
            """
            description = "daily EMAIL notifications over last 100 days"
        else:
            sql = """
            SELECT 
                DATE(mrl.log_timestamp) as notification_date, 
                COUNT(*) as email_count 
            FROM monitor_rules_logs mrl 
            WHERE mrl.channel = 'EMAIL' 
            GROUP BY DATE(mrl.log_timestamp) 
            ORDER BY notification_date DESC 
            LIMIT 30
            """
            description = "daily EMAIL notifications over time"
    
    elif 'most violated' in query_lower or 'violated most' in query_lower:
        sql = """
        SELECT 
            r.rule_name, 
            COUNT(mrl.log_id) as violation_count 
        FROM monitor_rules r 
        LEFT JOIN monitor_rules_logs mrl ON r.rule_id = mrl.rule_id 
        WHERE mrl.audit_type = 'VIOLATION' 
        GROUP BY r.rule_id, r.rule_name 
        ORDER BY violation_count DESC 
        LIMIT 10
        """
        description = "rules ranked by violation frequency"
    
    elif 'trends' in query_lower or 'over time' in query_lower:
        sql = """
        SELECT 
            DATE(mrl.log_timestamp) as violation_date, 
            COUNT(*) as violation_count 
        FROM monitor_rules_logs mrl 
        WHERE mrl.audit_type = 'VIOLATION' 
        GROUP BY DATE(mrl.log_timestamp) 
        ORDER BY violation_date DESC 
        LIMIT 30
        """
        description = "daily violation trends over last 30 days"
    
    elif 'channel' in query_lower and 'statistics' in query_lower:
        sql = """
        SELECT 
            mrl.channel, 
            COUNT(*) as notification_count, 
            AVG(CASE WHEN mrl.status = 'SENT' THEN 1 ELSE 0 END) as success_rate 
        FROM monitor_rules_logs mrl 
        WHERE mrl.audit_type = 'NOTIFICATION' 
        GROUP BY mrl.channel 
        ORDER BY notification_count DESC
        """
        description = "notification statistics by channel"
    
    else:
        # Default rules analytics query
        sql = """
        SELECT 
            r.rule_name, 
            r.is_violated,
            COUNT(mrl.log_id) as total_logs,
            COUNT(CASE WHEN mrl.audit_type = 'VIOLATION' THEN 1 END) as violation_count,
            COUNT(CASE WHEN mrl.audit_type = 'NOTIFICATION' THEN 1 END) as notification_count
        FROM monitor_rules r 
        LEFT JOIN monitor_rules_logs mrl ON r.rule_id = mrl.rule_id 
        GROUP BY r.rule_id, r.rule_name, r.is_violated 
        ORDER BY violation_count DESC
        """
        description = "comprehensive rules analytics with violation and notification counts"
    
    return sql, description


@tool
async def execute_rules_analytics_query(user_query: str) -> str:
    """Execute complex analytics queries for rules group."""
    try:
        print(f"🧠 Processing rules analytics query: '{user_query}'")
        
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
                "query_type": "rules_analytics",
                "tables_involved": ["monitor_rules", "rules_definitions", "rule_actions", "monitor_rules_logs", "monitored_feeds"]
            }
        }
        
        return json.dumps(response_data, indent=2, default=str)
        
    except Exception as e:
        error_msg = f"Error executing rules analytics query '{user_query}': {str(e)}"
        print(f"❌ {error_msg}")
        return json.dumps({
            "error": error_msg,
            "records": [],
            "query_description": "error occurred",
            "sql_query": sql_query if 'sql_query' in locals() else "N/A"
        }, indent=2, default=str)
