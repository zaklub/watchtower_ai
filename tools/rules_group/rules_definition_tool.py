"""
Dynamic SQL query generator for rules_definitions table based on user requests
"""

import json
import re
from typing import Tuple, List, Dict, Any
from langchain_core.tools import tool

from database.db_connection import DatabaseConnection
from ollama_client.ollama_client import OllamaClient


async def generate_sql_where_clause(user_query: str) -> Tuple[List[str], str]:
    """Use LLM to dynamically generate SQL WHERE clause conditions based on natural language query."""
    try:
        ollama_client = OllamaClient()
        
        system_prompt = """You are a SQL expert specializing in database queries for monitoring and rules systems.

IMPORTANT: You are working with POSTGRESQL database. Use PostgreSQL syntax.

Given a user's natural language query, generate appropriate SQL WHERE clause conditions for the rules_definitions table.

Table schema:
- definition_id: Unique definition identifier
- rule_id: Foreign key to monitor_rules.rule_id
- evaluator_id: Foreign key reference to rule_def_evaluator
- evaluation_query: Actual SQL query that will run on monitored_facts table to determine value to measure
- use_query: Tells us if this is a custom query defined by user or auto created
- evaluated_measure: The actual value with which the calculated measure is evaluated against
- evaluation_operator: The condition to evaluate like "=", "!=", ">", "<"
- definition_operator: Acts as AND/OR between definitions if more than 1 definition for one rule
- definition_name: Name of the definition

CRITICAL: You must return a COMPLETE and VALID JSON response. The JSON must be properly closed with all brackets and braces.

Expected JSON format (MUST be complete):
{
    "where_conditions": ["condition1", "condition2"],
    "query_description": "human readable description"
}

Examples:
- "Show me all rule definitions" → {"where_conditions": [], "query_description": "all rule definitions"}
- "Get definition for rule 123" → {"where_conditions": ["d.rule_id = 123"], "query_description": "definition for rule 123"}
- "Show me custom query definitions" → {"where_conditions": ["d.use_query = 'CUSTOM'"], "query_description": "custom query definitions"}
- "Find definitions with greater than operator" → {"where_conditions": ["d.evaluation_operator = '>'"], "query_description": "definitions with greater than operator"}
- "Definitions with AND grouping" → {"where_conditions": ["d.definition_operator = 'AND'"], "query_description": "definitions with AND grouping"}
- "Show me rule logic for rule X" → {"where_conditions": ["r.rule_name ILIKE '%X%'"], "query_description": "rule logic for rule X"}

Remember: Your response must be a COMPLETE JSON object. No partial responses.

User query: """

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
            query_description = parsed_response.get('query_description', 'rule definitions')
            
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
            if condition.startswith(('d.', 'r.', 'm.', 'DATE(')):
                conditions.append(condition)
        
        print(f"🔧 Extracted conditions: {conditions}")
        print(f"🔧 Extracted description: {description}")
        return conditions, description
    
    print("⚠️ Could not extract conditions or description, using fallback")
    return fallback_word_matching(user_query)


def fallback_word_matching(user_query: str) -> Tuple[List[str], str]:
    """Fallback word matching when LLM fails."""
    print("🔄 Using fallback word matching for rule definitions")
    query_lower = user_query.lower()
    where_conditions = []
    
    # Rule ID matching
    if 'rule' in query_lower and any(char.isdigit() for char in user_query):
        numbers = re.findall(r'\d+', user_query)
        if numbers:
            rule_id = numbers[0]
            where_conditions.append(f"d.rule_id = {rule_id}")
            return where_conditions, f"definition for rule {rule_id}"
    
    # Rule name matching
    if any(word in query_lower for word in ['rule logic', 'rule x', 'rule for']):
        quoted_names = re.findall(r'"([^"]+)"', user_query)
        if quoted_names:
            rule_name = quoted_names[0]
            where_conditions.append(f"r.rule_name ILIKE '%{rule_name}%'")
            return where_conditions, f"rule logic for '{rule_name}'"
        
        # Try to extract rule name from context
        if 'sap' in query_lower:
            where_conditions.append("r.rule_name ILIKE '%SAP%'")
            return where_conditions, "rule definitions for SAP monitors"
        elif 'cpu' in query_lower:
            where_conditions.append("r.rule_name ILIKE '%CPU%'")
            return where_conditions, "rule definitions for CPU monitors"
    
    # Status matching
    if any(word in query_lower for word in ['active', 'enabled', 'on']):
        where_conditions.append("d.is_active = 'TRUE'")
        return where_conditions, "active rule definitions"
    
    if any(word in query_lower for word in ['inactive', 'disabled', 'off']):
        where_conditions.append("d.is_active = 'FALSE'")
        return where_conditions, "inactive rule definitions"
    
    # Evaluation frequency matching
    frequency_mappings = {
        'real-time': 'REAL_TIME',
        'realtime': 'REAL_TIME',
        'hourly': 'HOURLY',
        'daily': 'DAILY'
    }
    
    for keyword, frequency in frequency_mappings.items():
        if keyword in query_lower:
            where_conditions.append(f"d.evaluation_frequency = '{frequency}'")
            return where_conditions, f"{keyword} evaluation rules"
    
    # Time-based matching
    time_mappings = {
        'today': ("DATE(d.created_at) = CURRENT_DATE", "rule definitions created today"),
        'today\'s': ("DATE(d.created_at) = CURRENT_DATE", "rule definitions created today"),
        'current': ("DATE(d.created_at) = CURRENT_DATE", "rule definitions created today"),
        'yesterday': ("DATE(d.created_at) = CURRENT_DATE - INTERVAL '1 day'", "rule definitions created yesterday"),
        'week': ("d.created_at >= NOW() - INTERVAL '7 days'", "rule definitions created in last week")
    }
    
    for keyword, (condition, description) in time_mappings.items():
        if keyword in query_lower:
            where_conditions.append(condition)
            return where_conditions, description
    
    # Default: show all rule definitions
    return where_conditions, "all rule definitions"


def _format_record(definition: Dict[str, Any]) -> Dict[str, Any]:
    """Format a single database record."""
    return {
        "definition_id": str(definition['definition_id']) if definition['definition_id'] is not None else None,
        "rule_id": float(definition['rule_id']) if definition['rule_id'] is not None else None,
        "rule_name": str(definition['rule_name']) if definition['rule_name'] is not None else None,
        "evaluator_id": str(definition['evaluator_id']) if definition['evaluator_id'] is not None else None,
        "evaluation_query": str(definition['evaluation_query']) if definition['evaluation_query'] is not None else None,
        "use_query": str(definition['use_query']) if definition['use_query'] is not None else None,
        "evaluated_measure": str(definition['evaluated_measure']) if definition['evaluated_measure'] is not None else None,
        "evaluation_operator": str(definition['evaluation_operator']) if definition['evaluation_operator'] is not None else None,
        "definition_operator": str(definition['definition_operator']) if definition['definition_operator'] is not None else None,
        "definition_name": str(definition['definition_name']) if definition['definition_name'] is not None else None
    }


@tool
async def query_rules_definition_dynamic(user_query: str) -> str:
    """Dynamically query rules definitions based on natural language."""
    try:
        print(f"🔍 Processing rules definition query: '{user_query}'")
        
        # Generate WHERE clause conditions
        where_conditions, query_description = await generate_sql_where_clause(user_query)
        
        # Build the SQL query
        base_query = """
        SELECT
            d.definition_id,
            d.rule_id,
            r.rule_name,
            d.evaluator_id,
            d.evaluation_query,
            d.use_query,
            d.evaluated_measure,
            d.evaluation_operator,
            d.definition_operator,
            d.definition_name
        FROM rules_definitions d
        LEFT JOIN monitor_rules r ON d.rule_id = r.rule_id
        """
        
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
        
        base_query += " ORDER BY d.definition_id LIMIT 100"
        
        print(f"🔍 Generated SQL: {base_query}")
        
        # Execute the query
        db_connection = DatabaseConnection()
        results = db_connection.execute_query(base_query)
        
        print(f"✅ Query executed, found {len(results)} results")
        
        # Format the results
        records = [_format_record(definition) for definition in results]
        
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
        error_msg = f"Error processing rules definition query '{user_query}': {str(e)}"
        print(f"❌ {error_msg}")
        return json.dumps({
            "error": error_msg,
            "records": [],
            "query_description": "error occurred"
        }, indent=2)
