"""
Simplified Watchtower AI API
Enhanced with NEW Two-Level Classification System
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio
import uuid
from typing import Dict, Optional

from config import API_CONFIG, CORS_CONFIG
from intent.classify_intent import classify_intent
from agents.new_tool_selector_agent import query_with_agent
from response_formatters import format_chart_response, format_text_response
from response_type_detector import detect_response_type
from ollama_client.ollama_client import OllamaClient

app = FastAPI(
    title=API_CONFIG["title"],
    description=API_CONFIG["description"],
    version=API_CONFIG["version"]
)

# Add CORS middleware to ignore CORS restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_CONFIG["allow_origins"],
    allow_credentials=CORS_CONFIG["allow_credentials"],
    allow_methods=CORS_CONFIG["allow_methods"],
    allow_headers=CORS_CONFIG["allow_headers"],
)

class QueryRequest(BaseModel):
    query: str

class StopRequest(BaseModel):
    session_id: Optional[str] = None

# Global storage for active tasks and sessions
active_tasks: Dict[str, asyncio.Task] = {}
session_tasks: Dict[str, str] = {}  # Maps session_id to task_id

def get_or_create_session_id(request: Request) -> str:
    """Get session ID from request headers or create a new one."""
    # Try to get session ID from custom header
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        # Generate a new session ID
        session_id = str(uuid.uuid4())
    return session_id

def cleanup_task(task_id: str):
    """Clean up completed or cancelled tasks."""
    global active_tasks, session_tasks
    if task_id in active_tasks:
        del active_tasks[task_id]
    # Remove from session mapping
    session_tasks = {k: v for k, v in session_tasks.items() if v != task_id}

async def generate_summary(user_query: str, records: list, query_description: str, chart_data: Optional[dict] = None) -> str:
    """Generate a summary of the data for any response type."""
    try:
        # If chart_data is provided, use it for summary instead of raw records
        if chart_data and isinstance(chart_data, dict) and 'labels' in chart_data and 'datasets' in chart_data:
            labels = chart_data.get('labels', [])
            datasets = chart_data.get('datasets', [])
            
            if not labels or not datasets:
                return f"No chart data available for the query: '{user_query}'"
            
            # Create summary based on chart data
            total_data_points = len(labels)
            summary = f"Chart shows {total_data_points} data points for '{query_description}'. "
            
            # Add information about the data range
            if labels:
                if len(labels) > 1:
                    summary += f"Data spans from {labels[0]} to {labels[-1]}. "
                else:
                    summary += f"Data point: {labels[0]}. "
            
            # Add information about dataset values
            if datasets:
                if isinstance(datasets, list) and len(datasets) > 0:
                    if isinstance(datasets[0], (int, float)):
                        # Single dataset with numeric values
                        max_val = max(datasets) if datasets else 0
                        min_val = min(datasets) if datasets else 0
                        avg_val = sum(datasets) / len(datasets) if datasets else 0
                        summary += f"Values range from {min_val} to {max_val} (average: {avg_val:.1f})."
                    else:
                        # Multiple datasets
                        summary += f"Contains {len(datasets)} data series."
                else:
                    summary += "No data values available."
            
            return summary
        
        # Fallback to original logic for non-chart responses
        if not records or len(records) == 0:
            return f"No data found for the query: '{user_query}'"
        
        # Create a simple summary based on the data
        total_count = len(records)
        
        # Get a sample of the data structure
        sample_record = records[0] if records else {}
        field_names = list(sample_record.keys()) if sample_record else []
        
        # Create a basic summary
        summary = f"Found {total_count} records for '{query_description}'. "
        
        if field_names:
            summary += f"The data includes fields: {', '.join(field_names[:5])}"  # Show first 5 fields
            if len(field_names) > 5:
                summary += f" and {len(field_names) - 5} more fields"
        
        return summary
        
    except Exception as e:
        return f"Summary generation failed: {str(e)}"

@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {"message": "Watchtower AI API with NEW Two-Level Classification is running!", "status": "healthy"}


@app.post("/query")
async def query_data(request: QueryRequest, http_request: Request):
    """Enhanced query endpoint with NEW two-level classification system."""
    # Get or create session ID
    session_id = get_or_create_session_id(http_request)
    
    # Create a unique task ID
    task_id = str(uuid.uuid4())
    
    # Clean up any existing task for this session
    if session_id in session_tasks:
        old_task_id = session_tasks[session_id]
        if old_task_id in active_tasks:
            active_tasks[old_task_id].cancel()
            cleanup_task(old_task_id)
    
    # Store the session-task mapping
    session_tasks[session_id] = task_id
    
    # Create and run the task
    task = asyncio.create_task(execute_query_logic(request))
    active_tasks[task_id] = task
    
    try:
        result = await task
        cleanup_task(task_id)
        return result
    except asyncio.CancelledError:
        cleanup_task(task_id)
        return JSONResponse(content={
            "type": "text",
            "response_type": "cancelled",
            "data": {
                "content": "Query execution was cancelled by user request."
            },
            "session_id": session_id
        })
    except Exception as e:
        cleanup_task(task_id)
        error_msg = str(e)
        error_type = type(e).__name__
        return JSONResponse(
            status_code=200,
            content={
                "type": "text",
                "response_type": "error_message",
                "data": {
                    "content": f"Unable to process your query due to a {error_type}: {error_msg}. Please try again or contact support if the issue persists."
                }
            }
        )

async def execute_query_logic(request: QueryRequest):
    """Execute the actual query logic."""
    try:
        intent = await classify_intent(request.query)
        # Log intent for monitoring purposes
        if intent == "monitoring_details":
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
            
            # Check if no records were returned from SQL query
            if not records or len(records) == 0:
                summary_text = await generate_summary(request.query, records, query_description)
                return JSONResponse(content={
                    "type": "text",
                    "response_type": "no_results",
                    "data": {
                        "content": f"No records found matching your query: '{request.query}'. Please try adjusting your search criteria or check if the data exists in the system."
                    },
                    "query_description": query_description,
                    "total_count": 0,
                    "metadata": metadata,
                    "summary": summary_text,
                    "generated_sql": generated_sql if generated_sql else None,
                    "sql_available": bool(generated_sql)
                })
            
            # Detect what type of response the user wants
            try:
                response_type = await detect_response_type(request.query, records)
            except (ConnectionError, ValueError) as e:
                # Handle specific errors from response type detection
                error_msg = str(e)
                return JSONResponse(
                    status_code=200,  # Changed to 200 for text response
                    content={
                        "type": "text",
                        "response_type": "connection_error",
                        "data": {
                            "content": f"Unable to process your query due to a connection issue: {error_msg}. The AI service is currently unavailable. Please try again later or contact support if the problem persists."
                        }
                    }
                )
            
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
                # Generate summary using the formatted chart data instead of raw records
                summary_text = await generate_summary(request.query, records, query_description, formatted_data)
                common_fields["summary"] = summary_text
                return JSONResponse(content={
                    "type": "chart",
                    "response_type": "chart",
                    "data": formatted_data,
                    **common_fields
                })
            elif response_type == "TEXT":
                formatted_data = format_text_response(records, query_description)
                # Generate summary using raw records for text responses
                summary_text = await generate_summary(request.query, records, query_description)
                common_fields["summary"] = summary_text
                return JSONResponse(content={
                    "type": "text",
                    "response_type": "summary",
                    "data": formatted_data,
                    **common_fields
                })
            else:  # TABLE (default)
                # Transform records into columns and rows format for frontend
                if records and len(records) > 0:
                    # Extract column names from the first record
                    columns = list(records[0].keys())
                    
                    # Transform records into rows format
                    rows = []
                    for record in records:
                        row = {}
                        for column in columns:
                            row[column] = record.get(column, None)
                        rows.append(row)
                else:
                    columns = []
                    rows = []
                
                # Generate summary using raw records for table responses
                summary_text = await generate_summary(request.query, records, query_description)
                common_fields["summary"] = summary_text
                return JSONResponse(content={
                    "type": "records",
                    "response_type": "table",
                    "data": {
                        "columns": columns,
                        "rows": rows
                    },
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
        
        elif intent == "database_schema":
            return JSONResponse(content={
                "type": "text",
                "response_type": "error",
                "data": {
                    "content": "This is a monitoring system, not a database management system. I can help you with monitoring rules, violations, performance data, and alerts. Please ask about monitoring-related topics instead."
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
        error_msg = str(e)
        error_type = type(e).__name__
        return JSONResponse(
            status_code=200,  # Changed to 200 for text response
            content={
                "type": "text",
                "response_type": "error_message",
                "data": {
                    "content": f"Unable to process your query due to a {error_type}: {error_msg}. Please try again or contact support if the issue persists."
                }
            }
        )

@app.post("/stop")
async def stop_query(request: StopRequest, http_request: Request):
    """Stop a running query for the current session."""
    try:
        # Get session ID from request or headers
        session_id = request.session_id or get_or_create_session_id(http_request)
        
        if session_id in session_tasks:
            task_id = session_tasks[session_id]
            if task_id in active_tasks:
                # Cancel the task
                active_tasks[task_id].cancel()
                cleanup_task(task_id)
                
                return JSONResponse(content={
                    "type": "text",
                    "response_type": "success",
                    "data": {
                        "content": f"Query execution stopped successfully for session {session_id}"
                    },
                    "session_id": session_id,
                    "stopped": True
                })
            else:
                return JSONResponse(content={
                    "type": "text",
                    "response_type": "error",
                    "data": {
                        "content": f"No active query found for session {session_id}"
                    },
                    "session_id": session_id,
                    "stopped": False
                })
        else:
            return JSONResponse(content={
                "type": "text",
                "response_type": "error",
                "data": {
                    "content": f"No session found with ID {session_id}"
                },
                "session_id": session_id,
                "stopped": False
            })
            
    except Exception as e:
        return JSONResponse(content={
            "type": "text",
            "response_type": "error",
            "data": {
                "content": f"Error stopping query: {str(e)}"
            },
            "stopped": False
        })

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and load balancers"""
    return {"status": "healthy", "service": "watchtower-ai-new-classification", "timestamp": "2024-01-01T00:00:00Z"}

# OPTIONS handlers for CORS preflight requests
@app.options("/")
async def options_root():
    """Handle CORS preflight requests for root endpoint"""
    return JSONResponse(content={}, status_code=200)

@app.options("/query")
async def options_query():
    """Handle CORS preflight requests for query endpoint"""
    return JSONResponse(content={}, status_code=200)

@app.options("/health")
async def options_health():
    """Handle CORS preflight requests for health endpoint"""
    return JSONResponse(content={}, status_code=200)

@app.options("/stop")
async def options_stop():
    """Handle CORS preflight requests for stop endpoint"""
    return JSONResponse(content={}, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
