"""
Simplified Watchtower AI API
Direct database tool integration without complex parsing
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import json

from config import API_CONFIG
from intent.classify_intent import classify_intent
from agents.tool_selector_agent import query_with_agent, test_agent_connection
from ollama_client.ollama_client import OllamaClient


async def detect_response_type(user_query: str, data_records: list) -> str:
    """Detect what type of response the user wants based on their query."""
    print(f"🔍 Starting response type detection for query: '{user_query}'")
    
    try:
        ollama_client = OllamaClient()
        print(f"✅ Ollama client initialized")
        
        # Create a prompt to determine response type
        response_type_prompt = f"""
You are a response type detector. Based on the user's query, determine what type of response they want.

User Query: "{user_query}"

Available Response Types:
1. TABLE - User wants to see data in a structured table format (e.g., "show me", "list", "get", "find", "display")
2. CHART - User wants to visualize data in charts/graphs (e.g., "chart", "graph", "plot", "visualize", "trend", "over time")
3. TEXT - User wants a summary or description (e.g., "summarize", "summarise", "describe", "explain", "what is", "how many", "give me a summary", "tell me about")

CRITICAL: You must respond with EXACTLY one of these three words: TABLE, CHART, or TEXT

IMPORTANT: Pay special attention to words like:
- "summarize", "summarise", "summary" → TEXT
- "describe", "explain", "what is" → TEXT  
- "how many", "total", "count" → TEXT
- "chart", "graph", "plot" → CHART
- "show me", "list", "get" → TABLE

Examples:
- "Show me all violated rules" → TABLE
- "Create a chart of violations over time" → CHART  
- "Summarize the current rule status" → TEXT
- "Summarise the events for channel EMAIL" → TEXT
- "Plot the trend of alerts by priority" → CHART
- "List all monitors" → TABLE
- "Explain what happened yesterday" → TEXT
- "Give me a summary of violations" → TEXT

Your response must be exactly one word: TABLE, CHART, or TEXT

Response type:"""

        print(f"📝 Prompt created, length: {len(response_type_prompt)} characters")
        
        response_type = await ollama_client.classify_intent(response_type_prompt)
        
        print(f"🔍 Raw LLM response: '{response_type}'")
        print(f"🔍 Response type: {type(response_type)}")
        print(f"🔍 Response length: {len(response_type) if response_type else 0}")
        
        if response_type:
            # Clean and normalize the response
            detected_type = response_type.strip().upper()
            print(f"🔍 Normalized response: '{detected_type}'")
            
            # Try to extract just the response type if LLM added extra text
            if len(detected_type) > 10:  # If response is too long, try to extract the type
                print("🔍 Response seems long, attempting to extract response type...")
                if 'TABLE' in detected_type:
                    detected_type = 'TABLE'
                elif 'CHART' in detected_type:
                    detected_type = 'CHART'
                elif 'TEXT' in detected_type:
                    detected_type = 'TEXT'
                print(f"🔍 Extracted response type: '{detected_type}'")
            
            # Check if it's a valid response type
            if detected_type in ['TABLE', 'CHART', 'TEXT']:
                print(f"🎯 LLM detected response type: {detected_type}")
                return detected_type
            else:
                print(f"⚠️ LLM returned invalid response type: '{detected_type}', using fallback")
        else:
            print("⚠️ LLM returned empty response, using fallback")
        
        # Fallback logic based on keywords
        print("🔄 Using fallback keyword logic...")
        query_lower = user_query.lower()
        
        # Chart/Visualization keywords
        chart_keywords = ['chart', 'graph', 'plot', 'visualize', 'trend', 'over time', 'by month', 'by day', 'show me a chart', 'create a chart', 'display chart']
        if any(word in query_lower for word in chart_keywords):
            print(f"🎯 Fallback detected response type: CHART")
            return "CHART"
        
        # Text/Summary keywords (including British spelling variations)
        text_keywords = [
            'summarize', 'summarise', 'summary', 'summaries',
            'describe', 'description', 'explain', 'explanation',
            'what is', 'what are', 'how many', 'how much',
            'total', 'count', 'overview', 'brief', 'briefly',
            'tell me about', 'give me a summary', 'provide summary',
            'sum up', 'summarise', 'summarize'
        ]
        if any(word in query_lower for word in text_keywords):
            print(f"🎯 Fallback detected response type: TEXT")
            return "TEXT"
        
        # Table/List keywords
        table_keywords = ['show me', 'list', 'get', 'find', 'display', 'view', 'see', 'show all', 'get all', 'list all']
        if any(word in query_lower for word in table_keywords):
            print(f"🎯 Fallback detected response type: TABLE")
            return "TABLE"
        
        # Default to TABLE if no clear indication
        print(f"🎯 Fallback detected response type: TABLE (default)")
        return "TABLE"
            
    except Exception as e:
        print(f"⚠️ Error detecting response type: {e}, defaulting to TABLE")
        return "TABLE"


def format_chart_response(data_records: list, query_description: str) -> dict:
    """Format data for chart visualization."""
    if not data_records:
        return {"chart_type": "empty", "message": "No data available for charting"}
    
    # Determine chart type based on data structure
    sample_record = data_records[0]
    
    # Check if we have timestamp data for time series
    has_timestamp = any('timestamp' in key.lower() for key in sample_record.keys())
    
    # Check if we have numeric data for bar/pie charts
    has_numeric = any(isinstance(value, (int, float)) and value is not None for value in sample_record.values())
    
    # Check if we have categorical data
    has_categorical = any(isinstance(value, str) and value in ['TRUE', 'FALSE', 'HIGH', 'MEDIUM', 'LOW', 'CRITICAL', 'EMAIL', 'SLACK', 'SMS'] for value in sample_record.values())
    
    chart_data = {
        "chart_type": "unknown",
        "title": f"{query_description.title()}",
        "data": data_records,
        "total_records": len(data_records),
        "chart_config": {}
    }
    
    if has_timestamp and has_numeric:
        chart_data["chart_type"] = "line_chart"
        chart_data["x_axis"] = "timestamp"
        chart_data["y_axis"] = "count"
        chart_data["chart_config"].update({
            "x_axis_label": "Time",
            "y_axis_label": "Count",
            "chart_style": "time_series"
        })
    elif has_categorical and has_numeric:
        chart_data["chart_type"] = "bar_chart"
        chart_data["x_axis"] = "category"
        chart_data["y_axis"] = "count"
        chart_data["chart_config"].update({
            "x_axis_label": "Category",
            "y_axis_label": "Count",
            "chart_style": "categorical"
        })
    elif has_categorical:
        chart_data["chart_type"] = "pie_chart"
        chart_data["dimension"] = "category"
        chart_data["chart_config"].update({
            "chart_style": "distribution",
            "show_percentages": True
        })
    else:
        chart_data["chart_type"] = "table"
        chart_data["chart_config"].update({
            "chart_style": "tabular",
            "sortable": True,
            "searchable": True
        })
    
    # Add specific chart configurations based on data content
    if 'priority' in sample_record:
        chart_data["chart_config"]["priority_colors"] = {
            "CRITICAL": "#ff0000",
            "HIGH": "#ff6600", 
            "MEDIUM": "#ffcc00",
            "LOW": "#00cc00"
        }
    
    if 'channel' in sample_record:
        chart_data["chart_config"]["channel_colors"] = {
            "EMAIL": "#0066cc",
            "SLACK": "#4a154b",
            "SMS": "#00cc66",
            "PAGERDUTY": "#06ac38",
            "OPSGENIE": "#ff6600"
        }
    
    return chart_data


def format_text_response(data_records: list, query_description: str) -> dict:
    """Format data as a text summary."""
    if not data_records:
        return {
            "summary": f"No {query_description} found.",
            "total_count": 0
        }
    
    total_count = len(data_records)
    
    # Create a meaningful summary based on the data
    summary_parts = [f"Found {total_count} {query_description}."]
    
    # Analyze the data for insights
    if data_records:
        sample_record = data_records[0]
        
        # Check for priority levels
        if 'priority' in sample_record:
            priorities = [record.get('priority') for record in data_records if record.get('priority')]
            if priorities:
                priority_counts = {}
                for priority in priorities:
                    priority_counts[priority] = priority_counts.get(priority, 0) + 1
                priority_summary = ", ".join([f"{count} {priority}" for priority, count in priority_counts.items()])
                summary_parts.append(f"Priority breakdown: {priority_summary}.")
        
        # Check for channels
        if 'channel' in sample_record:
            channels = [record.get('channel') for record in data_records if record.get('channel')]
            if channels:
                channel_counts = {}
                for channel in channels:
                    channel_counts[channel] = channel_counts.get(channel, 0) + 1
                channel_summary = ", ".join([f"{count} via {channel}" for channel, count in channel_counts.items()])
                summary_parts.append(f"Notifications: {channel_summary}.")
        
        # Check for violation status
        if 'is_violated' in sample_record:
            violated_count = sum(1 for record in data_records if record.get('is_violated') == 'TRUE')
            if violated_count > 0:
                summary_parts.append(f"Currently {violated_count} rules are violated.")
        
        # Check for enabled status
        if 'is_enabled' in sample_record:
            enabled_count = sum(1 for record in data_records if record.get('is_enabled') == 'TRUE')
            if enabled_count > 0:
                summary_parts.append(f"{enabled_count} monitors are currently enabled.")
    
    return {
        "summary": " ".join(summary_parts),
        "total_count": total_count,
        "query_description": query_description
    }


app = FastAPI(
    title=API_CONFIG["title"],
    description=API_CONFIG["description"],
    version=API_CONFIG["version"]
)

class QueryRequest(BaseModel):
    query: str

@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {"message": "Watchtower AI API is running!", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "watchtower-ai"}

@app.post("/query")
async def query_data(request: QueryRequest):
    """Enhanced query endpoint with intelligent response formatting."""
    try:
        intent = await classify_intent(request.query)
        print(f"Detected intent: {intent} for query: {request.query}")
        
        if intent == "monitoring_details":
            print(f"🤖 Using simple tool selector for intelligent tool selection: '{request.query}'")
            
            agent_response = await query_with_agent(request.query)
            
            # Handle both string and dict responses
            if isinstance(agent_response, dict):
                # Analytics tool returns dict directly
                json_data = agent_response
            else:
                # Other tools return string that needs parsing
                try:
                    json_data = json.loads(agent_response)
                except json.JSONDecodeError:
                    return JSONResponse(content={
                        "type": "text",
                        "response_type": "error",
                        "data": {"content": agent_response}
                    })
            
            # Extract records and metadata from enhanced tool response
            if isinstance(json_data, dict) and 'records' in json_data:
                records = json_data.get('records', [])
                query_description = json_data.get('query_description', 'monitoring data')
                metadata = json_data.get('response_metadata', {})
                # Extract SQL if available (analytics tool)
                generated_sql = json_data.get('sql_query', None)
            else:
                # Fallback for old format
                records = json_data if isinstance(json_data, list) else []
                query_description = 'monitoring data'
                metadata = {}
                generated_sql = None
            
            # Detect what type of response the user wants
            response_type = await detect_response_type(request.query, records)
            
            # Prepare common response fields
            common_fields = {
                "query_description": query_description,
                "total_count": len(records),
                "metadata": metadata
            }
            
            # Add SQL information if available
            if generated_sql:
                common_fields["generated_sql"] = generated_sql
                common_fields["sql_available"] = True
            else:
                common_fields["sql_available"] = False
            
            # Format response based on detected type
            if response_type == "CHART":
                formatted_data = format_chart_response(records, query_description)
                return JSONResponse(content={
                    "type": "chart",
                    "response_type": "chart",
                    "data": formatted_data,
                    **common_fields
                })
            elif response_type == "TEXT":
                formatted_data = format_text_response(records, query_description)
                return JSONResponse(content={
                    "type": "text",
                    "response_type": "summary",
                    "data": formatted_data,
                    **common_fields
                })
            else:  # TABLE (default)
                return JSONResponse(content={
                    "type": "records",
                    "response_type": "table",
                    "data": records,
                    **common_fields
                })
        
        elif intent == "create_rule":
            return JSONResponse(content={
                "type": "text",
                "response_type": "instruction",
                "data": {
                    "content": f"To create a new monitoring rule, you would need to configure: rule name, conditions, thresholds, and notification settings. Query: '{request.query}'"
                }
            })
        
        else:  # generic_question
            from config import GENERIC_RESPONSE
            return JSONResponse(content={
                "type": "text", 
                "response_type": "help",
                "data": GENERIC_RESPONSE
            })
            
    except Exception as e:
        print(f"❌ Error processing query: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "response_type": "error",
                "data": {
                    "error": str(e),
                    "message": "Failed to process query"
                }
            }
        )

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and load balancers"""
    return {"status": "healthy", "service": "watchtower-ai", "timestamp": "2024-01-01T00:00:00Z"}

@app.get("/test-agent")
async def test_agent():
    """Test the simple tool selector setup and tool access"""
    try:
        if test_agent_connection():
            return {"status": "success", "message": "Simple tool selector and tools are working correctly"}
        else:
            return {"status": "error", "message": "Tool selector setup failed"}
    except Exception as e:
        return {"status": "error", "message": f"Tool selector test failed: {str(e)}"}

@app.post("/debug-query")
async def debug_query(request: QueryRequest):
    """Debug endpoint to see what SQL is generated without full processing."""
    try:
        print(f"🔍 Debug query: '{request.query}'")
        
        # Get the raw agent response
        agent_response = await query_with_agent(request.query)
        
        if isinstance(agent_response, dict):
            # Analytics tool response
            return {
                "query": request.query,
                "tool_used": "analytics_tool",
                "generated_sql": agent_response.get("sql_query"),
                "query_description": agent_response.get("query_description"),
                "records_count": len(agent_response.get("records", [])),
                "full_response": agent_response
            }
        else:
            # Other tools response (string)
            try:
                parsed_response = json.loads(agent_response)
                return {
                    "query": request.query,
                    "tool_used": "other_tool",
                    "generated_sql": parsed_response.get("sql_query"),
                    "query_description": parsed_response.get("query_description"),
                    "records_count": len(parsed_response.get("records", [])),
                    "raw_response": agent_response,
                    "parsed_response": parsed_response
                }
            except json.JSONDecodeError:
                return {
                    "query": request.query,
                    "tool_used": "unknown",
                    "raw_response": agent_response,
                    "error": "Failed to parse response"
                }
                
    except Exception as e:
        return {
            "query": request.query,
            "error": str(e),
            "message": "Debug query failed"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
