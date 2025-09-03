"""
Dynamic SQL query generator for rule_actions table based on user requests
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

Given a user's natural language query, generate appropriate SQL WHERE clause conditions for the rule_actions table.

Table schema:
- action_id: Unique action identifier
- rules_id: Foreign key to monitor_rules.rule_id
- executor_id: Foreign key reference to action_executors.executor_id
- is_active: Action active or not (TRUE/FALSE)

IMPORTANT TABLE RELATIONSHIPS:
- rule_actions.rules_id → monitor_rules.rule_id (LEFT JOIN)
- rule_actions.executor_id → action_executors.executor_id (LEFT JOIN)
- action_executors.executor_name contains values like: "SEND_EMAIL", "SLACK_MESSAGE", "PAGERDUTY_TICKET", etc.

CRITICAL RULES:
1. You must return a COMPLETE and VALID JSON response. The JSON must be properly closed with all brackets and braces.
2. DO NOT include redundant join conditions like "r.rules_id = a.rules_id" - the LEFT JOIN already handles this relationship.
3. Use "e.executor_name" to filter by action types, NOT "a.action_name" (which doesn't exist).
4. The WHERE clause should only contain filtering conditions, not join conditions.

Expected JSON format (MUST be complete):
{
    "where_conditions": ["condition1", "condition2"],
    "query_description": "human readable description"
}

Examples:
- "Show me all rule actions" → {"where_conditions": [], "query_description": "all rule actions"}
- "Get actions for rule 123" → {"where_conditions": ["a.rules_id = 123"], "query_description": "actions for rule 123"}
- "Show me active rule actions" → {"where_conditions": ["a.is_active = 'TRUE'"], "query_description": "active rule actions"}
- "Actions for specific executor" → {"where_conditions": ["a.executor_id = 456"], "query_description": "actions for executor 456"}
- "What actions happen when rule X violates?" → {"where_conditions": ["r.rule_name ILIKE '%X%'"], "query_description": "actions for rule X"}
- "Rules with EMAIL actions" → {"where_conditions": ["e.executor_name = 'SEND_EMAIL'"], "query_description": "rules with SEND_EMAIL actions"}
- "Rules with SLACK actions" → {"where_conditions": ["e.executor_name = 'SLACK_MESSAGE'"], "query_description": "rules with SLACK_MESSAGE actions"}
- "List all the Rules which has actions as EMAIL" → {"where_conditions": ["e.executor_name = 'SEND_EMAIL'"], "query_description": "rules with SEND_EMAIL actions"}
- "Give me a List of all rules whose actions are 'SEND_EMAIL'" → {"where_conditions": ["e.executor_name = 'SEND_EMAIL'"], "query_description": "rules with SEND_EMAIL actions"}

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
                            if condition.startswith('a.') or condition.startswith('r.') or condition.startswith('m.') or condition.startswith('DATE('):
                                conditions.append(condition)
                        
                        print(f"🔧 Extracted conditions: {conditions}")
                        print(f"🔧 Extracted description: {description}")
                        return conditions, description
                    else:
                        print("⚠️ Could not extract conditions or description, using fallback")
                        return fallback_word_matching(user_query)
                
                where_conditions = parsed_response.get('where_conditions', [])
                query_description = parsed_response.get('query_description', 'rule actions')
                
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
    print("🔄 Using fallback word matching for rule actions")
    query_lower = user_query.lower()
    where_conditions = []
    
    # Rule ID matching
    if 'rule' in query_lower and any(char.isdigit() for char in user_query):
        import re
        numbers = re.findall(r'\d+', user_query)
        if numbers:
            rule_id = numbers[0]
            where_conditions.append(f"a.rules_id = {rule_id}")
            query_description = f"actions for rule {rule_id}"
    
    # Rule name matching
    elif any(word in query_lower for word in ['rule x', 'rule for', 'when rule']):
        import re
        quoted_names = re.findall(r'"([^"]+)"', user_query)
        if quoted_names:
            rule_name = quoted_names[0]
            where_conditions.append(f"r.rule_name ILIKE '%{rule_name}%'")
            query_description = f"actions for rule '{rule_name}'"
        else:
            # Try to extract rule name from context
            if 'sap' in query_lower:
                where_conditions.append("r.rule_name ILIKE '%SAP%'")
                query_description = "actions for SAP monitor rules"
            elif 'cpu' in query_lower:
                where_conditions.append("r.rule_name ILIKE '%CPU%'")
                query_description = "actions for CPU monitor rules"
            else:
                query_description = "rule actions"
    
    # Action type matching
    elif 'email' in query_lower:
        where_conditions.append("e.executor_name = 'SEND_EMAIL'")
        query_description = "email notification actions"
    elif 'slack' in query_lower:
        where_conditions.append("e.executor_name = 'SLACK_MESSAGE'")
        query_description = "SLACK notification actions"
    elif 'sms' in query_lower:
        where_conditions.append("e.executor_name = 'SMS_MESSAGE'")
        query_description = "SMS notification actions"
    elif 'pagerduty' in query_lower:
        where_conditions.append("e.executor_name = 'PAGERDUTY_TICKET'")
        query_description = "PagerDuty notification actions"
    elif 'opsgenie' in query_lower:
        where_conditions.append("e.executor_name = 'OPSGENIE_ALERTS'")
        query_description = "OpsGenie notification actions"
    
    # Active status matching
    elif any(word in query_lower for word in ['active', 'enabled', 'on']):
        where_conditions.append("a.is_active = 'TRUE'")
        query_description = "active rule actions"
    
    # Inactive status matching
    elif any(word in query_lower for word in ['inactive', 'disabled', 'off']):
        where_conditions.append("a.is_active = 'FALSE'")
        query_description = "inactive rule actions"
    
    # Time-based matching
    elif any(word in query_lower for word in ['today', 'today\'s', 'current']):
        where_conditions.append("DATE(a.created_at) = CURRENT_DATE")
        query_description = "rule actions created today"
    elif 'yesterday' in query_lower:
        where_conditions.append("DATE(a.created_at) = CURRENT_DATE - INTERVAL '1 day'")
        query_description = "rule actions created yesterday"
    elif 'week' in query_lower:
        where_conditions.append("a.created_at >= NOW() - INTERVAL '7 days'")
        query_description = "rule actions created in last week"
    
    # Default: show all rule actions
    if not where_conditions:
        query_description = "all rule actions"
    
    return where_conditions, query_description


@tool
async def query_rules_actions_dynamic(user_query: str) -> str:
    """Dynamically query rules actions based on natural language."""
    try:
        print(f"🔍 Processing rules actions query: '{user_query}'")
        
        # Generate WHERE clause conditions
        where_conditions, query_description = await generate_sql_where_clause(user_query)
        
        # Build the SQL query
        base_query = """
        SELECT
            a.action_id,
            a.rules_id,
            r.rule_name,
            a.executor_id,
            e.executor_name,
            a.is_active
        FROM rule_actions a
        LEFT JOIN monitor_rules r ON a.rules_id = r.rule_id
        LEFT JOIN action_executors e ON a.executor_id = e.executor_id
        """
        
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
        
        base_query += " ORDER BY a.action_id LIMIT 100"
        
        print(f"🔍 Generated SQL: {base_query}")
        
        # Execute the query
        db_connection = DatabaseConnection()
        results = db_connection.execute_query(base_query)
        
        print(f"✅ Query executed, found {len(results)} results")
        
        # Format the results
        records = []
        for action in results:
            records.append({
                "action_id": str(action['action_id']) if action['action_id'] is not None else None,
                "rules_id": float(action['rules_id']) if action['rules_id'] is not None else None,
                "rule_name": str(action['rule_name']) if action['rule_name'] is not None else None,
                "executor_id": str(action['executor_id']) if action['executor_id'] is not None else None,
                "executor_name": str(action['executor_name']) if action['executor_name'] is not None else None,
                "is_active": str(action['is_active']) if action['is_active'] is not None else None
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
        error_msg = f"Error processing rules actions query '{user_query}': {str(e)}"
        print(f"❌ {error_msg}")
        return json.dumps({
            "error": error_msg,
            "records": [],
            "query_description": "error occurred"
        }, indent=2)
