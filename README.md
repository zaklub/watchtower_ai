# Watchtower AI - Simplified

A simplified FastAPI application that provides direct access to monitoring rule data through natural language queries.

## Architecture

**Ultra-Simple Flow:**
```
User Query → Intent Classification (Ollama) → Direct Database Tool → Raw JSON Response
```

## Features

- **Direct Database Access**: No complex parsing or agents, just raw SQL results
- **Intent Classification**: Uses Ollama to classify user queries
- **Natural Language SQL**: Dynamic SQL generation based on user input
- **Raw JSON Output**: Returns exactly what the database provides

## Project Structure

```
watchtower_ai/
├── main.py                     # Simplified FastAPI app
├── config.py                   # Configuration settings
├── intent/                     # Intent classification
│   ├── classify_intent.py      # Ollama-based classification
│   └── fallback_intent_classification.py
├── database/                   # Database integration
│   └── db_connection.py        # PostgreSQL connection
├── tools/                      # Query tools
│   ├── monitor_feeds_tool.py  # Monitor configuration and settings
│   ├── rules_tool.py          # Monitor rules queries
│   └── rules_log_tool.py      # Historical logs and events
├── ollama_client/              # Ollama integration
│   └── ollama_client.py
└── requirements.txt            # Minimal dependencies
```

## Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure database and Ollama in `config.py`**

4. **Run the server:**
   ```bash
   python main.py
   ```

## API Usage

### Query Endpoint

**POST** `/query`

```json
{
  "query": "Show me all violated monitoring rules"
}
```

**Response:**
```json
{
  "type": "raw",
  "data": {
    "query_description": "violated rules",
    "total_count": 2,
    "summary": {
      "total_rules": 2,
      "violated_rules": 2,
      "active_rules": 2,
      "rules_with_reminders": 0
    },
    "records": [
      {
        "rule_id": 5001,
        "monitor_id": 2000.0,
        "rule_name": "SAP Order Payment Failure",
        "is_violated": "TRUE",
        "is_active": "TRUE",
        ...
      }
    ]
  }
}
```

## Supported Queries

### Monitor Configuration (monitor_feeds_tool)
- **Monitor Details**: "Show me all monitors", "Get enabled monitors", "List monitor configuration"
- **Monitor Types**: "Find monitors for transaction counting", "Show monitors for sum calculation"
- **Monitor Search**: "Find monitor by name 'CPU Usage'", "Show monitor details for ID 123"
- **Monitor Status**: "Get disabled monitors", "Show active monitors"

### Monitoring Rules (rules_tool)
- **Rule Status**: "Show me all rules", "Get violated rules", "List active monitors"
- **Rule Configuration**: "Find rules for monitor 123", "Show enabled rules"

### Historical Data (rules_log_tool)
- **Event History**: "Show violation logs", "Get audit history", "Show rollback events"
- **Alert History**: "Show email alerts", "Get recent violations"

### Other Operations
- **Create Rule**: "Create a new monitoring rule"
- **Generic Questions**: "What can you do?", "Help me understand"

## Database Schema

### monitored_feeds Table (Parent Table)
The `monitored_feeds` table contains all monitor configuration details:
- `monitor_id` (numeric, Primary Key): Unique monitor identifier
- `monitor_system_name` (varchar(100)): Name of the Monitor
- `monitor_description` (varchar(100)): Description of the Monitor
- `measure_transaction` (varchar(20)): TRUE = sum calculation, FALSE = event counting
- `measure_field_path` (varchar(400)): Path to calculate the measure
- `is_enabled` (varchar): Whether the monitor is enabled or not

### monitor_rules Table (Child Table)
The `monitor_rules` table contains rules created for each monitor:
- Links to `monitored_feeds` via `monitor_id` foreign key
- Contains rule configuration, status, and notification settings

### monitor_rules_logs Table
The `monitor_rules_logs` table contains historical events and audit logs:
- Links to `monitor_rules` via `rule_id` foreign key
- Tracks violations, alerts, and remediation actions

## Benefits

- ⚡ **Ultra Fast**: No parsing overhead, direct database results
- 🎯 **Accurate**: Exactly what the SQL query returns
- 🛡️ **Reliable**: Minimal code, fewer failure points
- 🔧 **Flexible**: Full access to all database fields and metadata