"""
Dynamic SQL query generator for monitor_rules_logs table based on user requests
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
        
        system_prompt = """You are a SQL expert specializing in database queries for monitoring and logging systems.

Given a user's natural language query, generate appropriate SQL WHERE clause conditions for the monitor_rules_logs table.

Table schema:
- log_id: Unique log identifier
- log_timestamp: Timestamp of the log  
- rule_id: Rule identifier
- rule_name: Rule name (from monitor_rules table)
- audit_type: Audit type
- log_comment: 'AUDIT' = OK, 'ROLLBACK' = fixed after violation, 'VIOLATED' = violated
- priority: Priority level (LOW, MEDIUM, HIGH, CRITICAL)
- channel: 'EMAIL', 'PAGERDUTY', 'SLACK', 'SMS', 'OPSGENIE'
- receiver: Receiver information
- description: Description of the event
- status: Current status
- alert_type: Type of alert
- app_incident_id: App incident identifier

CRITICAL: You must return a COMPLETE and VALID JSON response. The JSON must be properly closed with all brackets and braces.

Expected JSON format (MUST be complete):
{
    "where_conditions": ["condition1", "condition2"],
    "query_description": "human readable description"
}

Examples:
- "Show me all violated events" → {"where_conditions": ["l.log_comment = 'VIOLATED'"], "query_description": "violated events"}
- "Get audit logs from last week" → {"where_conditions": ["l.log_comment = 'AUDIT'", "l.log_timestamp >= NOW() - INTERVAL '7 days'"], "query_description": "audit logs from last week"}
- "Show me high priority email alerts from today" → {"where_conditions": ["l.priority IN ('HIGH', 'CRITICAL')", "l.channel = 'EMAIL'", "DATE(l.log_timestamp) = CURRENT_DATE"], "query_description": "high priority email alerts from today"}
- "Find logs for rule 5001" → {"where_conditions": ["l.rule_id = 5001"], "query_description": "logs for rule 5001"}
- "Show me recent violations by priority" → {"where_conditions": ["l.log_comment = 'VIOLATED'", "l.log_timestamp >= NOW() - INTERVAL '7 days'"], "query_description": "recent violations"}
- "Get all critical alerts sent via Slack" → {"where_conditions": ["l.priority = 'CRITICAL'", "l.channel = 'SLACK'"], "query_description": "critical Slack alerts"}
- "Show me violations that were fixed within the last 24 hours" → {"where_conditions": ["l.log_comment = 'ROLLBACK'", "l.log_timestamp >= NOW() - INTERVAL '24 hours'"], "query_description": "recently fixed violations"}
- "Give me a list of events for channel EMAIL in last one month" → {"where_conditions": ["l.channel = 'EMAIL'", "l.log_timestamp >= NOW() - INTERVAL '30 days'"], "query_description": "email events from last month"}

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
                            if condition.startswith('l.') or condition.startswith('DATE('):
                                conditions.append(condition)
                        
                        if conditions:
                            print(f"🔧 Manually extracted conditions: {conditions}")
                            print(f"🔧 Manually extracted description: {description}")
                            return conditions, description
                    
                    raise Exception("Could not extract valid conditions from incomplete JSON")
            else:
                parsed_response = json.loads(response_text)
            
            where_conditions = parsed_response.get("where_conditions", [])
            query_description = parsed_response.get("query_description", "logs based on LLM analysis")
            
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
    query_description = "logs"
    
    if any(word in query_lower for word in ['violated', 'violation', 'violations']):
        where_conditions.append("l.log_comment = 'VIOLATED'")
        query_description = "violated events"
        
    elif any(word in query_lower for word in ['audit', 'audits', 'ok']):
        where_conditions.append("l.log_comment = 'AUDIT'")
        query_description = "audit logs"
        
    elif any(word in query_lower for word in ['rollback', 'rollbacks', 'fixed']):
        where_conditions.append("l.log_comment = 'ROLLBACK'")
        query_description = "rollback events"
        
    elif any(word in query_lower for word in ['email']):
        where_conditions.append("l.channel = 'EMAIL'")
        query_description = "email alerts"
        
    elif any(word in query_lower for word in ['slack']):
        where_conditions.append("l.channel = 'SLACK'")
        query_description = "slack alerts"
        
    elif any(word in query_lower for word in ['sms']):
        where_conditions.append("l.channel = 'SMS'")
        query_description = "SMS alerts"
        
    elif any(word in query_lower for word in ['pagerduty']):
        where_conditions.append("l.channel = 'PAGERDUTY'")
        query_description = "PagerDuty alerts"
        
    elif any(word in query_lower for word in ['opsgenie']):
        where_conditions.append("l.channel = 'OPSGENIE'")
        query_description = "OpsGenie alerts"
        
    elif any(word in query_lower for word in ['high priority', 'critical']):
        where_conditions.append("l.priority IN ('HIGH', 'CRITICAL')")
        query_description = "high priority logs"
        
    elif any(word in query_lower for word in ['low priority']):
        where_conditions.append("l.priority = 'LOW'")
        query_description = "low priority logs"
        
    elif 'rule' in query_lower and any(char.isdigit() for char in user_query):
        import re
        rule_ids = re.findall(r'\d+', user_query)
        if rule_ids:
            rule_id = rule_ids[0]
            where_conditions.append(f"l.rule_id = {rule_id}")
            query_description = f"logs for rule {rule_id}"
            
    elif any(word in query_lower for word in ['recent', 'latest', 'last']):
        where_conditions.append("l.log_timestamp >= NOW() - INTERVAL '7 days'")
        query_description = "recent logs"
        
    elif 'month' in query_lower:
        if 'one month' in query_lower or '1 month' in query_lower:
            where_conditions.append("l.log_timestamp >= NOW() - INTERVAL '30 days'")
            query_description = "logs from last month"
        elif 'two month' in query_lower or '2 month' in query_lower:
            where_conditions.append("l.log_timestamp >= NOW() - INTERVAL '60 days'")
            query_description = "logs from last 2 months"
        else:
            where_conditions.append("l.log_timestamp >= NOW() - INTERVAL '30 days'")
            query_description = "logs from last month"
        
    elif any(word in query_lower for word in ['today']):
        where_conditions.append("DATE(l.log_timestamp) = CURRENT_DATE")
        query_description = "today's logs"
        
    elif any(word in query_lower for word in ['yesterday']):
        where_conditions.append("DATE(l.log_timestamp) = CURRENT_DATE - 1")
        query_description = "yesterday's logs"
    
    return where_conditions, query_description


@tool
async def query_monitor_rules_logs_dynamic(user_query: str) -> str:
    """Dynamically query the monitor_rules_logs table based on user's natural language request."""
    
    try:
        print(f"🔍 Dynamic query for logs: '{user_query}'")
        
        db = DatabaseConnection()
        
        base_query = """
        SELECT
            l.log_id,
            l.log_timestamp,
            l.rule_id,
            r.rule_name,
            l.audit_type,
            l.log_comment,
            l.priority,
            l.channel,
            l.receiver,
            l.description,
            l.status,
            l.alert_type,
            l.app_incident_id
        FROM monitor_rules_logs l
        LEFT JOIN monitor_rules r ON l.rule_id = r.rule_id
        """
        
        try:
            where_conditions, query_description = await generate_sql_where_clause(user_query)
            print(f"🤖 LLM generated SQL for: {query_description}")
        except Exception as e:
            print(f"❌ LLM-based generation failed: {e}")
            print(f"⚠️ Falling back to word-matching logic...")
            where_conditions, query_description = fallback_word_matching(user_query)
            print(f"🔄 Fallback generated: {query_description}")
        
        order_by = "ORDER BY l.log_timestamp DESC"
        limit_clause = "LIMIT 100"
        
        if where_conditions:
            where_clause = " WHERE " + " AND ".join(where_conditions)
        else:
            where_clause = ""
            
        final_query = f"{base_query}{where_clause} {order_by} {limit_clause}"
        
        print(f"🔍 SQL:\n{final_query}")
        
        results = db.execute_query(final_query)
        
        class DecimalEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, Decimal):
                    return float(o)
                return super(DecimalEncoder, self).default(o)
        
        records = []
        
        for log in results:
            records.append({
                "log_id": str(log['log_id']) if log['log_id'] is not None else None,
                "log_timestamp": str(log['log_timestamp']) if log['log_timestamp'] is not None else None,
                "rule_id": float(log['rule_id']) if log['rule_id'] is not None else None,
                "rule_name": str(log['rule_name']) if log['rule_name'] is not None else None,
                "audit_type": str(log['audit_type']) if log['audit_type'] is not None else None,
                "log_comment": str(log['log_comment']) if log['log_comment'] is not None else None,
                "priority": str(log['priority']) if log['priority'] is not None else None,
                "channel": str(log['channel']) if log['channel'] is not None else None,
                "receiver": str(log['receiver']) if log['receiver'] is not None else None,
                "description": str(log['description']) if log['description'] is not None else None,
                "status": str(log['status']) if log['status'] is not None else None,
                "alert_type": str(log['alert_type']) if log['alert_type'] is not None else None,
                "app_incident_id": str(log['app_incident_id']) if log['app_incident_id'] is not None else None
            })
        
        # Return enhanced response with records, metadata, and generated SQL
        response_data = {
            "records": records,
            "query_description": query_description,
            "total_count": len(records),
            "sql_query": final_query,  # Include the generated SQL
            "response_metadata": {
                "table_name": "monitor_rules_logs",
                "query_type": "historical_events",
                "sql_generated": True
            }
        }
        
        return json.dumps(response_data, cls=DecimalEncoder, indent=2)
        
    except Exception as e:
        error_msg = f"Error processing dynamic logs query '{user_query}': {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg
