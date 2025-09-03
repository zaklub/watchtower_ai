"""
New Two-Level Tool Selector Agent
First classifies the group, then determines the specific table or analytics within that group
"""

from intent.classify_group import classify_group
from intent.classify_table_within_group import classify_table_within_group

# Import existing tools
from tools.rules_tool import query_monitor_rules_dynamic
from tools.rules_log_tool import query_monitor_rules_logs_dynamic
from tools.monitor_feeds_tool import query_monitor_feeds_dynamic
from tools.monitor_facts_tool import query_monitor_facts_dynamic

# Import new group-specific tools
from tools.monitor_group.monitor_condition_tool import query_monitor_conditions_dynamic
from tools.monitor_group.monitor_analytics_tool import execute_monitor_analytics_query
from tools.rules_group.rules_definition_tool import query_rules_definition_dynamic
from tools.rules_group.rules_actions_tool import query_rules_actions_dynamic
from tools.rules_group.rules_analytics_tool import execute_rules_analytics_query
from tools.actions_group.action_executors_tool import query_action_executors_dynamic
from tools.facts_group.facts_analytics_tool import execute_facts_analytics_query
from tools.actions_group.actions_analytics_tool import execute_actions_analytics_query


async def select_tool_and_execute(user_query: str) -> str | dict:
    """Two-level tool selection: first classify group, then classify table within group."""
    try:
        print(f"🤖 New two-level tool selection for: '{user_query}'")
        
        # Step 1: Classify which group the query belongs to
        print(f"🔍 Step 1: Classifying group...")
        group = await classify_group(user_query)
        print(f"✅ Group classified as: {group}")
        
        # Step 2: Classify which table within the group should handle the query
        print(f"🔍 Step 2: Classifying table within {group}...")
        table_or_analytics = await classify_table_within_group(group, user_query)
        print(f"✅ Table/analytics classified as: {table_or_analytics}")
        
        # Step 3: Execute the appropriate tool based on group and table
        print(f"🔧 Executing tool for {group} -> {table_or_analytics}")
        return await _execute_tool(group, table_or_analytics, user_query)
        
    except Exception as e:
        error_msg = f"Error in new two-level tool selection: {str(e)}"
        print(f"❌ {error_msg}")
        return f'{{"error": "{error_msg}"}}'


async def _execute_tool(group: str, table_or_analytics: str, user_query: str) -> str | dict:
    """Execute the appropriate tool based on group and table classification."""
    
    if group == "MONITOR_GROUP":
        return await _execute_monitor_group_tool(table_or_analytics, user_query)
    elif group == "FACTS_GROUP":
        return await _execute_facts_group_tool(table_or_analytics, user_query)
    elif group == "RULES_GROUP":
        return await _execute_rules_group_tool(table_or_analytics, user_query)
    elif group == "ACTIONS_GROUP":
        return await _execute_actions_group_tool(table_or_analytics, user_query)
    else:
        print(f"❓ Unknown group: {group}, defaulting to monitored feeds")
        return await query_monitor_feeds_dynamic.ainvoke({"user_query": user_query})


async def _execute_monitor_group_tool(table_or_analytics: str, user_query: str) -> str | dict:
    """Execute tools within MONITOR_GROUP."""
    if table_or_analytics == "MONITORED_FEEDS":
        print(f"📊 Executing monitored feeds tool for: '{user_query}'")
        return await query_monitor_feeds_dynamic.ainvoke({"user_query": user_query})
    elif table_or_analytics == "MONITOR_CONDITIONS":
        print(f"📊 Executing monitor conditions tool for: '{user_query}'")
        return await query_monitor_conditions_dynamic.ainvoke({"user_query": user_query})
    elif table_or_analytics == "ANALYTICS":
        print(f"🧠 Executing monitor analytics tool for: '{user_query}'")
        return await execute_monitor_analytics_query.ainvoke({"user_query": user_query})
    else:
        print(f"❓ Unknown monitor table: {table_or_analytics}, defaulting to monitored feeds")
        return await query_monitor_feeds_dynamic.ainvoke({"user_query": user_query})


async def _execute_facts_group_tool(table_or_analytics: str, user_query: str) -> str | dict:
    """Execute tools within FACTS_GROUP."""
    if table_or_analytics == "MONITOR_FACTS":
        print(f"📊 Executing monitor facts tool for: '{user_query}'")
        return await query_monitor_facts_dynamic.ainvoke({"user_query": user_query})
    elif table_or_analytics == "ANALYTICS":
        print(f"🧠 Executing facts analytics tool for: '{user_query}'")
        return await execute_facts_analytics_query.ainvoke({"user_query": user_query})
    else:
        print(f"❓ Unknown facts table: {table_or_analytics}, defaulting to monitor facts")
        return await query_monitor_facts_dynamic.ainvoke({"user_query": user_query})


async def _execute_rules_group_tool(table_or_analytics: str, user_query: str) -> str | dict:
    """Execute tools within RULES_GROUP."""
    if table_or_analytics == "MONITOR_RULES":
        print(f"📊 Executing monitor rules tool for: '{user_query}'")
        return await query_monitor_rules_dynamic.ainvoke({"user_query": user_query})
    elif table_or_analytics == "RULES_DEFINITIONS":
        print(f"📊 Executing rules definition tool for: '{user_query}'")
        return await query_rules_definition_dynamic.ainvoke({"user_query": user_query})
    elif table_or_analytics == "RULES_ACTIONS":
        print(f"📊 Executing rules actions tool for: '{user_query}'")
        return await query_rules_actions_dynamic.ainvoke({"user_query": user_query})
    elif table_or_analytics == "ACTION_EXECUTORS":
        print(f"📊 Executing action executors tool for: '{user_query}'")
        return await query_action_executors_dynamic.ainvoke({"user_query": user_query})
    elif table_or_analytics == "MONITOR_RULES_LOGS":
        print(f"📜 Executing monitor rule logs tool for: '{user_query}'")
        return await query_monitor_rules_logs_dynamic.ainvoke({"user_query": user_query})
    elif table_or_analytics == "ANALYTICS":
        print(f"🧠 Executing rules analytics tool for: '{user_query}'")
        return await execute_rules_analytics_query.ainvoke({"user_query": user_query})
    else:
        print(f"❓ Unknown rules table: {table_or_analytics}, defaulting to monitor rules")
        return await query_monitor_rules_dynamic.ainvoke({"user_query": user_query})


async def _execute_actions_group_tool(table_or_analytics: str, user_query: str) -> str | dict:
    """Execute tools within ACTIONS_GROUP."""
    if table_or_analytics == "ACTION_EXECUTORS":
        print(f"📊 Executing action executors tool for: '{user_query}'")
        return await query_action_executors_dynamic.ainvoke({"user_query": user_query})
    elif table_or_analytics == "ANALYTICS":
        print(f"🧠 Executing actions analytics tool for: '{user_query}'")
        return await execute_actions_analytics_query.ainvoke({"user_query": user_query})
    else:
        print(f"❓ Unknown actions table: {table_or_analytics}, defaulting to action executors")
        return await query_action_executors_dynamic.ainvoke({"user_query": user_query})


async def query_with_agent(user_query: str) -> str | dict:
    """Use new two-level tool selection to process a user query and return results."""
    return await select_tool_and_execute(user_query)
