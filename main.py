"""
Simplified Watchtower AI API
Enhanced with NEW Two-Level Classification System
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import json

from config import API_CONFIG
from intent.classify_intent import classify_intent
from agents.new_tool_selector_agent import query_with_agent
from response_formatters import format_chart_response, format_text_response
from response_type_detector import detect_response_type

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
    return {"message": "Watchtower AI API with NEW Two-Level Classification is running!", "status": "healthy"}


@app.post("/query")
async def query_data(request: QueryRequest):
    """Enhanced query endpoint with NEW two-level classification system."""
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
            
            # Detect what type of response the user wants
            try:
                response_type = await detect_response_type(request.query, records)
            except (ConnectionError, ValueError) as e:
                # Handle specific errors from response type detection
                error_msg = str(e)
                return JSONResponse(
                    status_code=503 if "connection" in error_msg.lower() else 400,
                    content={
                        "type": "error",
                        "response_type": "detection_failed",
                        "data": {
                            "error": error_msg,
                            "message": "Failed to detect response type",
                            "details": "Ollama service unavailable" if "connection" in error_msg.lower() else "Invalid response from LLM"
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
            status_code=500,
            content={
                "type": "error",
                "response_type": "processing_error",
                "data": {
                    "error": error_msg,
                    "error_type": error_type,
                    "message": "Failed to process query",
                    "details": "Unexpected error occurred during query processing"
                }
            }
        )

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and load balancers"""
    return {"status": "healthy", "service": "watchtower-ai-new-classification", "timestamp": "2024-01-01T00:00:00Z"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
