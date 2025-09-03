"""
Advanced Analytics Tool for Watchtower AI
Handles complex multi-table queries with JOINs, GROUP BY, aggregations
"""

import json
import asyncio
from decimal import Decimal
from typing import Dict, Any, List, Optional

from database.db_connection import DatabaseConnection
from ollama_client.ollama_client import OllamaClient


class AnalyticsTool:
    """Advanced analytics tool for complex multi-table queries."""
    
    def __init__(self):
        """Initialize the analytics tool with full table knowledge."""
        self.ollama_client = OllamaClient()
        self.setup_table_knowledge()
    
    def setup_table_knowledge(self):
        """Set up comprehensive knowledge of all tables and relationships."""
        self.table_schema = {
            "monitored_feeds": {
                "description": "Monitor configuration and settings",
                "columns": {
                    "monitor_id": "Primary key, unique monitor identifier",
                    "monitor_system_name": "Human-readable monitor name",
                    "monitor_description": "Description of what the monitor does",
                    "measure_transaction": "TRUE/FALSE - whether it measures transactions",
                    "measure_field_path": "Field path for measurement",
                    "is_enabled": "TRUE/FALSE - whether monitor is active"
                },
                "relationships": ["monitor_rules", "monitor_rules_logs", "monitored_facts"]
            },
            "monitor_rules": {
                "description": "Current monitoring rules and their status",
                "columns": {
                    "rule_id": "Primary key, unique rule identifier",
                    "monitor_id": "Foreign key to monitored_feeds.monitor_id",
                    "rule_name": "Name of the rule",
                    "is_violated": "TRUE/FALSE - current violation status",
                    "execute_on": "When the rule executes (e.g., 'daily', 'hourly')",
                    "is_active": "TRUE/FALSE - whether rule is active",
                    "do_remind": "TRUE/FALSE - whether to send reminders",
                    "interval_mins": "Reminder interval in minutes",
                    "use_calendar": "TRUE/FALSE - whether to use calendar",
                    "calendar_name": "Name of associated calendar",
                    "is_enabled": "TRUE/FALSE - whether rule is enabled"
                },
                "relationships": ["monitored_feeds", "monitor_rules_logs"]
            },
            "monitor_rules_logs": {
                "description": "Historical events, audit trails, and alerts",
                "columns": {
                    "log_id": "Primary key, unique log entry identifier",
                    "log_timestamp": "When the event occurred",
                    "rule_id": "Foreign key to monitor_rules.rule_id",
                    "audit_type": "Type of audit event",
                    "log_comment": "Description of the event",
                    "priority": "Priority level (HIGH, MEDIUM, LOW, CRITICAL)",
                    "channel": "Notification channel (EMAIL, SLACK, SMS)",
                    "receiver": "Who received the notification",
                    "description": "Detailed description",
                    "status": "Status of the event",
                    "alert_type": "Type of alert generated",
                    "app_incident_id": "External incident identifier"
                },
                "relationships": ["monitor_rules", "monitored_feeds"]
            },
            "monitored_facts": {
                "description": "Actual measured values and event counts for monitors over time ranges",
                "columns": {
                    "fact_id": "Primary key, unique fact identifier (character varying 50)",
                    "monitor_id": "Foreign key to monitored_feeds.monitor_id (numeric)",
                    "start_time": "Start time of the collection range (timestamp)",
                    "end_time": "End time of the collection range (timestamp)",
                    "cummulative_measure": "Cumulative count or sum value (numeric)",
                    "samples": "Number of samples/events for this monitor (character varying 32)"
                },
                "relationships": ["monitored_feeds"]
            }
        }
        
        self.relationships = {
            "monitored_feeds → monitor_rules": "monitored_feeds.monitor_id = monitor_rules.monitor_id",
            "monitor_rules → monitor_rules_logs": "monitor_rules.rule_id = monitor_rules_logs.rule_id",
            "monitored_feeds → monitor_rules_logs": "monitored_feeds.monitor_id = monitor_rules.monitor_id AND monitor_rules.rule_id = monitor_rules_logs.rule_id",
            "monitored_feeds → monitored_facts": "monitored_feeds.monitor_id = monitored_facts.monitor_id"
        }
    
    async def generate_complex_sql(self, user_query: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Generate complex SQL for analytics queries using LLM."""
        try:
            system_prompt = f"""You are an expert SQL analyst specializing in complex multi-table queries with JOINs, GROUP BY, aggregations, and subqueries.

IMPORTANT: You are working with POSTGRESQL database. Use PostgreSQL syntax, NOT MySQL syntax.

You have access to these tables and their relationships:

{json.dumps(self.table_schema, indent=2)}

Table Relationships:
{json.dumps(self.relationships, indent=2)}

Your task is to generate COMPLEX SQL queries that may involve:
- Multiple table JOINs
- GROUP BY with aggregations (COUNT, SUM, AVG, MAX, MIN)
- HAVING clauses for filtering aggregated results
- Subqueries and CTEs
- ORDER BY for ranking and sorting
- Window functions if needed

CRITICAL: You must return ONLY a valid JSON object. Do not add any text before or after the JSON.

REQUIRED FORMAT (copy exactly):
{{
    "sql_query": "YOUR_COMPLETE_SQL_QUERY_HERE",
    "query_description": "Human readable description of what this query finds",
    "query_type": "analytics|comparison|trend|ranking|distribution"
}}

IMPORTANT RULES:
1. Start with {{ and end with }}
2. Use double quotes for all strings
3. No trailing commas
4. No extra text before or after the JSON
5. Ensure all quotes are properly escaped in SQL
6. Use POSTGRESQL syntax (NOT MySQL)

POSTGRESQL SPECIFIC SYNTAX EXAMPLES:
- Date arithmetic: NOW() - INTERVAL '30 days' (NOT DATE_SUB)
- String concatenation: str1 \|\| str2 (NOT CONCAT)
- Current date: CURRENT_DATE or NOW()
- Date extraction: EXTRACT(DAY FROM timestamp)
- Interval: INTERVAL '1 month', INTERVAL '7 days'

Examples of complex queries you should handle:
- "Which monitor has the most rules?" → JOIN + GROUP BY + COUNT + ORDER BY + LIMIT
- "Violation rates by monitor priority" → JOIN + GROUP BY + COUNT + HAVING
- "Monitors with more than 5 rules" → JOIN + GROUP BY + COUNT + HAVING
- "Average rules per monitor type" → JOIN + GROUP BY + AVG
- "Top 3 most problematic monitors" → JOIN + GROUP BY + COUNT + ORDER BY + LIMIT
- "Show me monitor performance over time" → JOIN + monitored_facts + time series analysis
- "Which monitors have the highest event counts?" → JOIN + monitored_facts + GROUP BY + ORDER BY
- "Monitor throughput trends by hour" → JOIN + monitored_facts + time grouping + aggregations
- "Compare monitor performance across different time periods" → JOIN + monitored_facts + date comparisons

User Query: """

            full_prompt = system_prompt + user_query
            
            print(f"🧠 Analytics Tool: Generating complex SQL for: '{user_query}'")
            
            llm_response = await self.ollama_client.classify_intent(full_prompt)
            
            if not llm_response:
                print("⚠️ LLM failed to respond for analytics query")
                return None, None, None
            
            # Extract JSON from response
            response_text = llm_response.strip()
            import re
            
            # More robust JSON extraction - find the first { and last }
            start_brace = response_text.find('{')
            end_brace = response_text.rfind('}')
            
            if start_brace == -1 or end_brace == -1 or start_brace >= end_brace:
                print(f"⚠️ Could not find valid JSON braces in response: {response_text}")
                return None, None, None
            
            json_str = response_text[start_brace:end_brace + 1]
            print(f"🔍 Extracted JSON: {json_str}")
            
            # Clean up common LLM formatting issues
            json_str = json_str.replace('\n', ' ').replace('\r', ' ')
            json_str = re.sub(r'\s+', ' ', json_str)  # Normalize whitespace
            
            try:
                parsed_response = json.loads(json_str)
                
                sql_query = parsed_response.get("sql_query")
                query_description = parsed_response.get("query_description")
                query_type = parsed_response.get("query_type")
                
                if sql_query and query_description:
                    print(f"✅ Generated SQL: {sql_query[:100]}...")
                    print(f"✅ Query description: {query_description}")
                    print(f"✅ Query type: {query_type}")
                    return sql_query, query_description, query_type
                else:
                    print("⚠️ Missing required fields in LLM response")
                    return None, None, None
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"🔍 Raw JSON string that failed: '{json_str}'")
                print(f"🔍 JSON string length: {len(json_str)}")
                print(f"🔍 JSON string type: {type(json_str)}")
                
                # Try to fix common LLM formatting issues
                try:
                    # Remove any trailing commas before closing braces
                    fixed_json = re.sub(r',\s*}', '}', json_str)
                    fixed_json = re.sub(r',\s*]', ']', fixed_json)
                    
                    print(f"🔧 Attempting to fix JSON: '{fixed_json}'")
                    parsed_response = json.loads(fixed_json)
                    
                    sql_query = parsed_response.get("sql_query")
                    query_description = parsed_response.get("query_description")
                    query_type = parsed_response.get("query_type")
                    
                    if sql_query and query_description:
                        print(f"✅ Fixed JSON parsing successful!")
                        print(f"✅ Generated SQL: {sql_query[:100]}...")
                        print(f"✅ Query description: {query_description}")
                        print(f"✅ Query type: {query_type}")
                        return sql_query, query_description, query_type
                        
                except json.JSONDecodeError as fix_error:
                    print(f"❌ JSON fix attempt also failed: {fix_error}")
                
                return None, None, None
                
        except Exception as e:
            print(f"❌ Error generating complex SQL: {str(e)}")
            return None, None, None
    
    def _generate_fallback_sql(self, user_query: str) -> tuple[str, str, str]:
        """Generate fallback SQL when LLM fails."""
        print("🔄 Using fallback SQL generation for analytics query")
        
        query_lower = user_query.lower()
        
        # Simple fallback patterns
        if "most rules" in query_lower or "highest rule count" in query_lower:
            sql = """
                SELECT m.monitor_system_name, COUNT(r.rule_id) as rule_count
                FROM monitored_feeds m 
                JOIN monitor_rules r ON m.monitor_id = r.monitor_id 
                GROUP BY m.monitor_id, m.monitor_system_name 
                ORDER BY rule_count DESC 
                LIMIT 1
            """
            description = "Monitor with the highest number of rules"
            query_type = "ranking"
            
        elif "more than" in query_lower and "rules" in query_lower:
            # Extract number from query
            import re
            number_match = re.search(r'more than (\d+)', query_lower)
            threshold = number_match.group(1) if number_match else 3
            
            sql = f"""
                SELECT m.monitor_system_name, COUNT(r.rule_id) as rule_count
                FROM monitored_feeds m 
                JOIN monitor_rules r ON m.monitor_id = r.monitor_id 
                GROUP BY m.monitor_id, m.monitor_system_name 
                HAVING COUNT(r.rule_id) > {threshold}
                ORDER BY rule_count DESC
            """
            description = f"Monitors with more than {threshold} rules"
            query_type = "analytics"
            
        elif "performance" in query_lower or "throughput" in query_lower or "events" in query_lower:
            # Monitor performance/throughput queries
            sql = """
                SELECT m.monitor_system_name, 
                       AVG(f.cummulative_measure) as avg_measure,
                       SUM(f.samples::numeric) as total_samples,
                       COUNT(f.fact_id) as fact_count
                FROM monitored_feeds m 
                JOIN monitored_facts f ON m.monitor_id = f.monitor_id 
                GROUP BY m.monitor_id, m.monitor_system_name 
                ORDER BY avg_measure DESC
            """
            description = "Monitor performance and throughput analysis"
            query_type = "analytics"
            
        elif "time" in query_lower and ("trend" in query_lower or "over" in query_lower):
            # Time-based trend queries
            sql = """
                SELECT m.monitor_system_name,
                       DATE_TRUNC('hour', f.start_time) as hour_bucket,
                       AVG(f.cummulative_measure) as avg_measure,
                       COUNT(f.fact_id) as fact_count
                FROM monitored_feeds m 
                JOIN monitored_facts f ON m.monitor_id = f.monitor_id 
                WHERE f.start_time >= NOW() - INTERVAL '24 hours'
                GROUP BY m.monitor_id, m.monitor_system_name, DATE_TRUNC('hour', f.start_time)
                ORDER BY m.monitor_system_name, hour_bucket
            """
            description = "Monitor performance trends over time"
            query_type = "trend"
            
        else:
            # Generic fallback
            sql = """
                SELECT m.monitor_system_name, COUNT(r.rule_id) as rule_count
                FROM monitored_feeds m 
                JOIN monitor_rules r ON m.monitor_id = r.monitor_id 
                GROUP BY m.monitor_id, m.monitor_system_name 
                ORDER BY rule_count DESC
            """
            description = "Monitor rule counts"
            query_type = "analytics"
        
        return sql.strip(), description, query_type
    
    async def execute_analytics_query(self, user_query: str) -> Dict[str, Any]:
        """Execute a complex analytics query."""
        try:
            print(f"🚀 Analytics Tool: Executing complex query: '{user_query}'")
            
            # Generate complex SQL
            sql_query, query_description, query_type = await self.generate_complex_sql(user_query)
            
            if not sql_query:
                print("🔄 LLM SQL generation failed, trying fallback...")
                sql_query, query_description, query_type = self._generate_fallback_sql(user_query)
                
                if not sql_query:
                    return {
                        "error": "Failed to generate SQL for analytics query",
                        "query": user_query
                    }
            
            # Execute the query
            print(f"📊 Executing analytics query: {sql_query[:100]}...")
            
            db_connection = DatabaseConnection()
            
            try:
                # Execute query and get results directly
                results = db_connection.execute_query(sql_query)
                
                if not results:
                    print("⚠️ Query returned no results")
                    records = []
                    column_names = []
                else:
                    # Get column names from first result
                    column_names = list(results[0].keys()) if results else []
                    records = results
                
                print(f"✅ Analytics query executed successfully, returned {len(records)} rows")
                
                # Prepare response
                response = {
                    "query_type": "analytics",
                    "query_description": query_description,
                    "analytics_type": query_type,
                    "sql_query": sql_query,
                    "records": records,
                    "total_count": len(records),
                    "columns": column_names,
                    "response_metadata": {
                        "tool_used": "analytics_tool",
                        "query_complexity": "complex",
                        "tables_involved": self._extract_tables_from_sql(sql_query)
                    }
                }
                
                return response
                
            except Exception as e:
                print(f"❌ Database query execution failed: {str(e)}")
                raise
                
        except Exception as e:
            print(f"❌ Error executing analytics query: {str(e)}")
            return {
                "error": f"Analytics query execution failed: {str(e)}",
                "query": user_query
            }
    
    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table names from SQL query."""
        tables = []
        sql_upper = sql.upper()
        
        if "MONITORED_FEEDS" in sql_upper:
            tables.append("monitored_feeds")
        if "MONITOR_RULES" in sql_upper:
            tables.append("monitor_rules")
        if "MONITOR_RULES_LOGS" in sql_upper:
            tables.append("monitor_rules_logs")
        if "MONITORED_FACTS" in sql_upper:
            tables.append("monitored_facts")
        
        return tables
    
# Convenience function for easy integration
async def execute_analytics_query(user_query: str) -> Dict[str, Any]:
    """Execute an analytics query using the analytics tool."""
    tool = AnalyticsTool()
    return await tool.execute_analytics_query(user_query)
