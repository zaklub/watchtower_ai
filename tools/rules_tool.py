"""
Dynamic SQL query generator for monitor_rules table based on user requests
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
        
        system_prompt = """You are a SQL expert specializing in database queries for monitoring and rules systems.

IMPORTANT: You are working with POSTGRESQL database. Use PostgreSQL syntax.

Given a user's natural language query, generate appropriate SQL WHERE clause conditions for the monitor_rules table.

IMPORTANT: When filtering by monitor name, use m.monitor_system_name (from the monitored_feeds table), NOT r.monitor_name.

Table schema:
- rule_id: Unique rule identifier
- monitor_id: Monitor identifier (links to monitored_feeds)
- rule_name: Rule name
- is_violated: Current violation status (TRUE/FALSE)
- execute_on: Execution time
- is_active: Active status (TRUE/FALSE)
- do_remind: Reminder status (TRUE/FALSE)
- interval_mins: Reminder interval in minutes
- use_calendar: Calendar usage flag (TRUE/FALSE)
- calendar_name: Calendar name associated with the rule
- is_enabled: Enabled status (TRUE/FALSE)

CRITICAL: You must return a COMPLETE and VALID JSON response. The JSON must be properly closed with all brackets and braces.

Expected JSON format (MUST be complete):
{
    "where_conditions": ["condition1", "condition2"],
    "query_description": "human readable description"
}

Examples:
- "Show me violated rules" → {"where_conditions": ["r.is_violated = 'TRUE'"], "query_description": "violated rules"}
- "Get all active rules" → {"where_conditions": ["r.is_active = 'TRUE'"], "query_description": "active rules"}
- "Find rules for monitor 123" → {"where_conditions": ["r.monitor_id = 123"], "query_description": "rules for monitor 123"}
- "Show rules with reminders enabled" → {"where_conditions": ["r.do_remind = 'TRUE'"], "query_description": "rules with reminders enabled"}
- "Get enabled rules that are not violated" → {"where_conditions": ["r.is_enabled = 'TRUE'", "r.is_violated = 'FALSE'"], "query_description": "enabled non-violated rules"}
- "Find rules for SAP monitor" → {"where_conditions": ["m.monitor_system_name LIKE '%SAP%'"], "query_description": "rules for SAP monitor"}
- "Get all rules for 'SAP Order Payment Failure Monitor'" → {"where_conditions": ["m.monitor_system_name = 'SAP Order Payment Failure Monitor'"], "query_description": "rules for SAP Order Payment Failure Monitor"}
- "Show me rules that execute daily" → {"where_conditions": ["r.execute_on LIKE '%daily%'"], "query_description": "daily executing rules"}
- "Get rules with 15 minute intervals" → {"where_conditions": ["r.interval_mins = 15"], "query_description": "rules with 15 minute intervals"}

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
                            if condition.startswith('r.') or condition.startswith('m.'):
                                conditions.append(condition)
                        
                        if conditions:
                            print(f"🔧 Manually extracted conditions: {conditions}")
                            print(f"🔧 Manually extracted description: {description}")
                            return conditions, description
                    
                    raise Exception("Could not extract valid conditions from incomplete JSON")
            else:
                parsed_response = json.loads(response_text)
            
            where_conditions = parsed_response.get("where_conditions", [])
            query_description = parsed_response.get("query_description", "rules based on LLM analysis")
            
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
    query_description = "rules"
    
    if any(word in query_lower for word in ['violated', 'violation', 'problem', 'alert', 'issue', 'broken', 'failed']):
        where_conditions.append("r.is_violated = 'TRUE'")
        query_description = "violated rules"
        
    elif any(word in query_lower for word in ['active', 'running', 'enabled']):
        where_conditions.append("r.is_active = 'TRUE'")
        query_description = "active rules"
        
    elif any(word in query_lower for word in ['inactive', 'disabled', 'stopped']):
        where_conditions.append("r.is_active = 'FALSE'")
        query_description = "inactive rules"
        
    elif any(word in query_lower for word in ['remind', 'reminder', 'notification']):
        where_conditions.append("r.do_remind = 'TRUE'")
        query_description = "rules with reminders enabled"
        
    elif 'monitor' in query_lower and any(char.isdigit() for char in user_query):
        import re
        monitor_ids = re.findall(r'\d+', user_query)
        if monitor_ids:
            monitor_id = monitor_ids[0]
            where_conditions.append(f"r.monitor_id = {monitor_id}")
            query_description = f"rules for monitor {monitor_id}"
            
    elif any(word in query_lower for word in ['all', 'every', 'total', 'complete', 'entire']):
        where_conditions = []
        query_description = "all rules"
        
    else:
        where_conditions = []
        query_description = f"all rules (interpreted from: '{user_query}')"
    
    return where_conditions, query_description


@tool
async def query_monitor_rules_dynamic(user_query: str) -> str:
    """Dynamically query the monitor_rules table based on user's natural language request."""
    
    try:
        print(f"🔍 Dynamic query for rules: '{user_query}'")
        
        db = DatabaseConnection()
        
        base_query = """
        SELECT 
            r.rule_id,
            r.monitor_id,
            m.monitor_system_name as monitor_name,
            r.rule_name,
            r.is_violated,
            r.execute_on,
            r.is_active,
            r.do_remind,
            r.interval_mins,
            r.use_calandar as use_calendar,
            r.calandar_name as calendar_name,
            r.is_enabled
        FROM monitor_rules r
        LEFT JOIN monitored_feeds m ON r.monitor_id = m.monitor_id
        """
        
        try:
            where_conditions, query_description = await generate_sql_where_clause(user_query)
            print(f"🤖 LLM generated SQL for: {query_description}")
        except Exception as e:
            print(f"❌ LLM-based generation failed: {e}")
            print(f"⚠️ Falling back to word-matching logic...")
            where_conditions, query_description = fallback_word_matching(user_query)
            print(f"🔄 Fallback generated: {query_description}")
        
        order_by = "ORDER BY r.rule_id"
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
            return f"No monitoring rules found for query: {query_description}"
        
        class DecimalEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, Decimal):
                    return float(o)
                return super(DecimalEncoder, self).default(o)
        
        records = []
        
        for rule in results:
            records.append({
                "rule_id": int(rule['rule_id']) if rule['rule_id'] is not None else None,
                "monitor_id": float(rule['monitor_id']) if rule['monitor_id'] is not None else None,
                "monitor_name": str(rule['monitor_name']) if rule['monitor_name'] is not None else None,
                "rule_name": str(rule['rule_name']) if rule['rule_name'] is not None else None,
                "is_violated": str(rule['is_violated']) if rule['is_violated'] is not None else None,
                "is_active": str(rule['is_active']) if rule['is_active'] is not None else None,
                "do_remind": str(rule['do_remind']) if rule['do_remind'] is not None else None,
                "execute_on": str(rule['execute_on']) if rule['execute_on'] is not None else None,
                "interval_mins": float(rule['interval_mins']) if rule['interval_mins'] is not None else None,
                "use_calendar": str(rule['use_calendar']) if rule['use_calendar'] is not None else None,
                "calendar_name": str(rule['calendar_name']) if rule['calendar_name'] is not None else None,
                "is_enabled": str(rule['is_enabled']) if rule['is_enabled'] is not None else None
            })
        
        # Return enhanced response with records, metadata, and generated SQL
        response_data = {
            "records": records,
            "query_description": query_description,
            "total_count": len(records),
            "sql_query": final_query,  # Include the generated SQL
            "response_metadata": {
                "table_name": "monitor_rules",
                "query_type": "rule_status",
                "sql_generated": True
            }
        }
        
        return json.dumps(response_data, cls=DecimalEncoder, indent=2)
        
    except Exception as e:
        error_msg = f"Error processing dynamic rules query '{user_query}': {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg
