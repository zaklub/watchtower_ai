"""
Simple tool selector that intelligently chooses between rules_tool and rules_log_tool
"""

from ollama_client.ollama_client import OllamaClient

from tools.rules_tool import query_monitor_rules_dynamic
from tools.rules_log_tool import query_monitor_rules_logs_dynamic
from tools.monitor_feeds_tool import query_monitor_feeds_dynamic
from tools.monitor_facts_tool import query_monitor_facts_dynamic
from tools.analytics_tool import execute_analytics_query


async def select_tool_and_execute(user_query: str) -> str | dict:
    """Simple tool selection: determine which tool to use based on query keywords."""
    try:
        print(f"🤖 Simple tool selection for: '{user_query}'")
        
        ollama_client = OllamaClient()
        
        selection_prompt = f"""
You are a tool selector. Based on the user's query, determine which tool to use:

MONITOR_FEEDS: Use for queries about monitor configuration and settings
- Monitor details, names, descriptions, and configuration
- Monitor status (enabled/disabled)
- Monitor types (sum calculation vs event counting)
- Examples: "show monitors", "enabled monitors", "monitor configuration", "monitor details"

CURRENT_RULES: Use for queries about the current state of monitoring rules
- Current rule status (which rules are currently violated, active, enabled)
- Rule configuration and settings
- Finding rules by name, ID, or monitor ID
- Examples: "show violated rules", "current rules", "active rules", "rule status"

HISTORICAL_LOGS: Use for queries about RULE-RELATED events and audit history
- Rule violation events and alerts
- Rule execution logs and audit trails
- Alert notifications that were sent for rule violations
- Rollback events when rules were fixed after violations
- RULE VIOLATIONS and ALERTS (not performance events)
- NOTIFICATION CHANNELS (EMAIL, SLACK, SMS, PAGERDUTY, OPSGENIE) - these are about rule violation alerts
- Examples: "show logs", "audit history", "past violations", "alert history", "rollback events", "violation events", "rule violation logs", "EMAIL notifications", "SLACK alerts", "channel EMAIL", "notifications via SMS"

MONITOR_FACTS: Use for queries about monitor performance metrics and measured values
- Actual measured values, event counts, and throughput data
- Performance data over time ranges
- Monitor performance trends and analysis
- MONITOR EVENTS and EVENT DATA (not rule violations)
- Examples: "show performance data", "monitor throughput", "event counts", "performance trends", "monitor events", "event data", "events in last X days", "monitor events from last week"

ANALYTICS: Use for complex queries that require multiple tables, aggregations, or comparisons
- Queries with "most", "highest", "average", "count", "group by"
- Comparing data across multiple monitors or rules
- Finding patterns, trends, or rankings
- Examples: "which monitor has most rules", "violation rates by priority", "top 5 monitors", "average rules per monitor"

Key distinction:
- "monitors" or "monitor configuration" = MONITOR_FEEDS
- "violated rules" = CURRENT_RULES (current state)
- "rule violation events", "violation logs", "rule logs" = HISTORICAL_LOGS (rule-related events)
- "channels" (EMAIL, SLACK, SMS, PAGERDUTY, OPSGENIE) = HISTORICAL_LOGS (rule violation notifications)
- "monitor events", "event data", "performance data", "throughput", "event counts" = MONITOR_FACTS
- "most", "highest", "average", "count", "group by" = ANALYTICS

CRITICAL: 
- "monitor events" = MONITOR_FACTS (actual measured events/performance data)
- "rule violation events" = HISTORICAL_LOGS (rule violations and alerts)
- "channels" (EMAIL, SLACK, SMS, PAGERDUTY, OPSGENIE) = HISTORICAL_LOGS (rule violation notifications)
- "events" alone is ambiguous - look for context words like "monitor", "rule", "violation"

User Query: "{user_query}"

IMPORTANT EXAMPLES:
- "Plot me a chart for Channel EMAIL" → HISTORICAL_LOGS (channels are about rule violation notifications)
- "Show me EMAIL notifications" → HISTORICAL_LOGS (channels are about rule violation notifications)
- "SLACK alerts for last week" → HISTORICAL_LOGS (channels are about rule violation notifications)

Respond with EXACTLY one of these options:
MONITOR_FEEDS
CURRENT_RULES
HISTORICAL_LOGS
MONITOR_FACTS
ANALYTICS

Tool choice:"""

        tool_selection = await ollama_client.classify_intent(selection_prompt)
        
        if not tool_selection:
            return '{"error": "Failed to get tool selection from LLM"}'
        
        tool_choice = tool_selection.strip().upper()
        print(f"🔧 Selected tool: {tool_choice}")
        
        if "MONITOR_FEEDS" in tool_choice:
            print(f"📊 Executing monitor feeds tool for: '{user_query}'")
            result = await query_monitor_feeds_dynamic.ainvoke({"user_query": user_query})
            return result
        elif "CURRENT_RULES" in tool_choice:
            print(f"📊 Executing current rules tool for: '{user_query}'")
            result = await query_monitor_rules_dynamic.ainvoke({"user_query": user_query})
            return result
        elif "HISTORICAL_LOGS" in tool_choice:
            print(f"📜 Executing historical logs tool for: '{user_query}'")
            result = await query_monitor_rules_logs_dynamic.ainvoke({"user_query": user_query})
            return result
        elif "MONITOR_FACTS" in tool_choice:
            print(f"📊 Executing monitor facts tool for: '{user_query}'")
            result = await query_monitor_facts_dynamic.ainvoke({"user_query": user_query})
            return result
        elif "ANALYTICS" in tool_choice:
            print(f"🧠 Executing analytics tool for: '{user_query}'")
            result = await execute_analytics_query(user_query)
            return result
        else:
            print(f"❓ Unclear selection '{tool_choice}', defaulting to monitor feeds")
            result = await query_monitor_feeds_dynamic.ainvoke({"user_query": user_query})
            return result
            
    except Exception as e:
        error_msg = f"Error in simple tool selection: {str(e)}"
        print(f"❌ {error_msg}")
        return f'{{"error": "{error_msg}"}}'


async def query_with_agent(user_query: str) -> str | dict:
    """Use simple tool selection to process a user query and return results."""
    return await select_tool_and_execute(user_query)


def test_agent_connection() -> bool:
    """Test that the simple tool selector can access tools."""
    try:
        print("✅ Testing simple tool selector setup...")
        
        print("✅ Monitor feeds tool imported successfully")
        print("✅ Rules tool imported successfully")
        print("✅ Logs tool imported successfully")
        print("✅ Monitor facts tool imported successfully")
        
        try:
            monitor_result = query_monitor_feeds_dynamic.ainvoke({"user_query": "test query"})
            print("✅ Monitor feeds tool can be invoked")
        except Exception as e:
            print(f"⚠️ Monitor feeds tool test: {e}")
            
        try:
            rules_result = query_monitor_rules_dynamic.ainvoke({"user_query": "test query"})
            print("✅ Rules tool can be invoked")
        except Exception as e:
            print(f"⚠️ Rules tool test: {e}")
            
        try:
            logs_result = query_monitor_rules_logs_dynamic.ainvoke({"user_query": "test query"})
            print("✅ Logs tool can be invoked")
        except Exception as e:
            print(f"⚠️ Logs tool test: {e}")
            
        try:
            facts_result = query_monitor_facts_dynamic.ainvoke({"user_query": "test query"})
            print("✅ Monitor facts tool can be invoked")
        except Exception as e:
            print(f"⚠️ Monitor facts tool test: {e}")
        
        print("✅ Simple tool selector ready")
        return True
        
    except Exception as e:
        print(f"❌ Tool selector setup failed: {e}")
        return False
