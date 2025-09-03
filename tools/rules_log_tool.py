"""
Dynamic SQL query generator for monitor_rules_logs table based on user requests
"""

import json
import re
from decimal import Decimal
from typing import Tuple, List, Dict, Any
from langchain_core.tools import tool

from database.db_connection import DatabaseConnection
from ollama_client.ollama_client import OllamaClient


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle Decimal types."""
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def _create_system_prompt() -> str:
    """Create the system prompt for LLM-based SQL generation."""
    return """You are a SQL expert specializing in database queries for monitoring and logging systems.

IMPORTANT: You are working with POSTGRESQL database. Use PostgreSQL syntax.

Given a user's natural language query, generate appropriate SQL WHERE clause conditions for the monitor_rules_logs table.

Table schema:
- log_id: Unique log identifier
- log_timestamp: Timestamp of the log  
- rule_id: Rule identifier
- rule_name: Rule name (from monitor_rules table)
- monitor_id: Monitor identifier (from monitor_rules table)
- monitor_name: Monitor system name (from monitored_feeds table, use m.monitor_system_name in WHERE clauses)
- audit_type: Audit type
- log_comment: 'AUDIT' = OK, 'ROLLBACK' = fixed after violation, 'VIOLATED' = rule failed/violated (use this for failed rules)
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
- "Show me logs for SAP monitor" → {"where_conditions": ["m.monitor_system_name ILIKE '%SAP%'"], "query_description": "logs for SAP monitor"}
- "Show me violations for CPU monitor" → {"where_conditions": ["l.log_comment = 'VIOLATED'", "m.monitor_system_name ILIKE '%CPU%'"], "query_description": "violations for CPU monitor"}
- "Give me the list of all the Monitors for which the rules have failed in last 2 months" → {"where_conditions": ["l.log_comment = 'VIOLATED'", "l.log_timestamp >= NOW() - INTERVAL '2 months'"], "query_description": "monitors with failed rules in last 2 months"}

Remember: Your response must be a COMPLETE JSON object. No partial responses.

User query: """


def _parse_llm_response(llm_response: str, user_query: str) -> Tuple[List[str], str]:
    """Parse LLM response and extract SQL conditions."""
    try:
        response_text = llm_response.strip()
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            print("⚠️ No JSON found in LLM response, using fallback")
            return fallback_word_matching(user_query)
        
        json_str = json_match.group(0)
        print(f"🔍 Extracted JSON: {json_str}")
        
        # Fix incomplete JSON if needed
        if not json_str.strip().endswith('}'):
            json_str += '}'
            print(f"🔧 Fixed incomplete JSON: {json_str}")
        
        try:
            parsed_response = json.loads(json_str)
            where_conditions = parsed_response.get('where_conditions', [])
            query_description = parsed_response.get('query_description', 'logs based on LLM analysis')
            
            print(f"✅ LLM generated {len(where_conditions)} conditions")
            return where_conditions, query_description
            
        except json.JSONDecodeError:
            print("🔧 Attempting to extract where_conditions from incomplete JSON...")
            return _extract_conditions_from_text(json_str, user_query)
                
    except Exception as e:
        print(f"⚠️ Error parsing LLM response: {e}, using fallback")
        return fallback_word_matching(user_query)


def _extract_conditions_from_text(json_str: str, user_query: str) -> Tuple[List[str], str]:
    """Extract conditions from malformed JSON text."""
    conditions_match = re.search(r'"where_conditions":\s*\[(.*?)\]', json_str, re.DOTALL)
    description_match = re.search(r'"query_description":\s*"([^"]*)"', json_str)
    
    if conditions_match and description_match:
        conditions_str = conditions_match.group(1)
        description = description_match.group(1)
        
        conditions = []
        condition_matches = re.findall(r'"([^"]*)"', conditions_str)
        for condition in condition_matches:
            if condition.startswith(('l.', 'r.', 'm.', 'DATE(')):
                conditions.append(condition)
        
        print(f"🔧 Extracted conditions: {conditions}")
        print(f"🔧 Extracted description: {description}")
        return conditions, description
    
    print("⚠️ Could not extract conditions or description, using fallback")
    return fallback_word_matching(user_query)


async def generate_sql_where_clause(user_query: str) -> Tuple[List[str], str]:
    """Use LLM to dynamically generate SQL WHERE clause conditions based on natural language query."""
    try:
        ollama_client = OllamaClient()
        system_prompt = _create_system_prompt()
        full_prompt = system_prompt + user_query
        
        print(f"🤖 Sending query to LLM for SQL generation: '{user_query}'")
        
        llm_response = await ollama_client.classify_intent(full_prompt)
        
        if not llm_response:
            print("⚠️ LLM failed to respond, using fallback word matching")
            return fallback_word_matching(user_query)
        
        return _parse_llm_response(llm_response, user_query)
            
    except Exception as e:
        print(f"⚠️ Error in SQL generation: {e}, using fallback")
        return fallback_word_matching(user_query)


def fallback_word_matching(user_query: str) -> Tuple[List[str], str]:
    """Fallback method using word-matching logic when LLM is unavailable."""
    query_lower = user_query.lower()
    where_conditions = []
    
    # Log comment matching
    comment_mappings = {
        'violated': ('l.log_comment = \'VIOLATED\'', 'violated events'),
        'violation': ('l.log_comment = \'VIOLATED\'', 'violated events'),
        'violations': ('l.log_comment = \'VIOLATED\'', 'violated events'),
        'failed': ('l.log_comment = \'VIOLATED\'', 'failed events'),
        'failures': ('l.log_comment = \'VIOLATED\'', 'failed events'),
        'audit': ('l.log_comment = \'AUDIT\'', 'audit logs'),
        'audits': ('l.log_comment = \'AUDIT\'', 'audit logs'),
        'ok': ('l.log_comment = \'AUDIT\'', 'audit logs'),
        'rollback': ('l.log_comment = \'ROLLBACK\'', 'rollback events'),
        'rollbacks': ('l.log_comment = \'ROLLBACK\'', 'rollback events'),
        'fixed': ('l.log_comment = \'ROLLBACK\'', 'rollback events')
    }
    
    for keyword, (condition, description) in comment_mappings.items():
        if keyword in query_lower:
            where_conditions.append(condition)
            return where_conditions, description
    
    # Channel matching
    channel_mappings = {
        'email': ('l.channel = \'EMAIL\'', 'email alerts'),
        'slack': ('l.channel = \'SLACK\'', 'slack alerts'),
        'sms': ('l.channel = \'SMS\'', 'SMS alerts'),
        'pagerduty': ('l.channel = \'PAGERDUTY\'', 'PagerDuty alerts'),
        'opsgenie': ('l.channel = \'OPSGENIE\'', 'OpsGenie alerts')
    }
    
    for keyword, (condition, description) in channel_mappings.items():
        if keyword in query_lower:
            where_conditions.append(condition)
            return where_conditions, description
    
    # Priority matching
    if any(word in query_lower for word in ['high priority', 'critical']):
        where_conditions.append("l.priority IN ('HIGH', 'CRITICAL')")
        return where_conditions, "high priority logs"
    
    if 'low priority' in query_lower:
        where_conditions.append("l.priority = 'LOW'")
        return where_conditions, "low priority logs"
    
    # Rule ID matching
    if 'rule' in query_lower and any(char.isdigit() for char in user_query):
        rule_ids = re.findall(r'\d+', user_query)
        if rule_ids:
            rule_id = rule_ids[0]
            where_conditions.append(f"l.rule_id = {rule_id}")
            return where_conditions, f"logs for rule {rule_id}"
    
    # Time-based matching
    time_mappings = {
        'recent': ("l.log_timestamp >= NOW() - INTERVAL '7 days'", "recent logs"),
        'latest': ("l.log_timestamp >= NOW() - INTERVAL '7 days'", "recent logs"),
        'last': ("l.log_timestamp >= NOW() - INTERVAL '7 days'", "recent logs"),
        'today': ("DATE(l.log_timestamp) = CURRENT_DATE", "today's logs"),
        'yesterday': ("DATE(l.log_timestamp) = CURRENT_DATE - 1", "yesterday's logs")
    }
    
    for keyword, (condition, description) in time_mappings.items():
        if keyword in query_lower:
            where_conditions.append(condition)
            return where_conditions, description
    
    # Month-based matching
    if 'month' in query_lower:
        if 'one month' in query_lower or '1 month' in query_lower:
            where_conditions.append("l.log_timestamp >= NOW() - INTERVAL '30 days'")
            return where_conditions, "logs from last month"
        elif 'two month' in query_lower or '2 month' in query_lower:
            where_conditions.append("l.log_timestamp >= NOW() - INTERVAL '60 days'")
            return where_conditions, "logs from last 2 months"
        else:
            where_conditions.append("l.log_timestamp >= NOW() - INTERVAL '30 days'")
            return where_conditions, "logs from last month"
    
    # Default: show all logs
    return where_conditions, "all logs"


def _format_log_record(log: Dict[str, Any]) -> Dict[str, Any]:
    """Format a single log record."""
    return {
        "log_id": str(log['log_id']) if log['log_id'] is not None else None,
        "log_timestamp": str(log['log_timestamp']) if log['log_timestamp'] is not None else None,
        "rule_id": float(log['rule_id']) if log['rule_id'] is not None else None,
        "rule_name": str(log['rule_name']) if log['rule_name'] is not None else None,
        "monitor_id": float(log['monitor_id']) if log['monitor_id'] is not None else None,
        "monitor_name": str(log['monitor_name']) if log['monitor_name'] is not None else None,
        "audit_type": str(log['audit_type']) if log['audit_type'] is not None else None,
        "log_comment": str(log['log_comment']) if log['log_comment'] is not None else None,
        "priority": str(log['priority']) if log['priority'] is not None else None,
        "channel": str(log['channel']) if log['channel'] is not None else None,
        "receiver": str(log['receiver']) if log['receiver'] is not None else None,
        "description": str(log['description']) if log['description'] is not None else None,
        "status": str(log['status']) if log['status'] is not None else None,
        "alert_type": str(log['alert_type']) if log['alert_type'] is not None else None,
        "app_incident_id": str(log['app_incident_id']) if log['app_incident_id'] is not None else None
    }


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
            r.monitor_id,
            m.monitor_system_name as monitor_name,
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
        
        # Build final query
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        final_query = f"{base_query}{where_clause} ORDER BY l.log_timestamp DESC LIMIT 100"
        
        print(f"🔍 SQL:\n{final_query}")
        
        results = db.execute_query(final_query)
        
        # Format the results
        records = [_format_log_record(log) for log in results]
        
        # Prepare response data
        response_data = {
            "records": records,
            "query_description": query_description,
            "total_count": len(records),
            "sql_query": final_query,
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