"""
Configuration file for Watchtower AI API
"""

# Ollama Configuration
OLLAMA_CONFIG = {
    "base_url": "http://172.20.150.10:11434",
    "model": "llama3:8b",  # Change this to your preferred model
    "timeout": 30.0
}

# Database Configuration
DATABASE_CONFIG = {
    "host": "wt-postgres",
    "port": 5432,
    "dbname": "wtdb",
    "user": "audituser",
    "password": "manageaudit"
}

# API Configuration
API_CONFIG = {
    "title": "Flexible Query API",
    "description": "API for querying data with responses in table, chart, or text formats, determined by the LLM based on the query string.",
    "version": "1.0.0",
    "host": "0.0.0.0",
    "port": 8000
}

# CORS Configuration
CORS_CONFIG = {
    "allow_origins": ["*"],  # Allow all origins - change to specific domains for production
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Specific methods instead of *
    "allow_headers": ["*"]  # Allow all headers
}

# Intent Classification Keywords
INTENT_KEYWORDS = {
    "create_rule": ['create', 'set', 'setup', 'configure', 'add', 'new', 'alert', 'watch'],
    "monitoring_details": ['show', 'get', 'view', 'display', 'chart', 'report', 'violations', 'status', 'data', 'analytics', 'list', 'rules', 'monitor', 'most', 'highest', 'average', 'count', 'group by', 'which', 'what', 'how many', 'give me', 'plot', 'graph', 'visualize', 'trend'],
    "chart": ['chart', 'graph', 'plot', 'trend', 'visual', 'show', 'display'],
    "table": ['table', 'list', 'breakdown', 'details', 'data', 'rows']
}

# Generic Question Response
GENERIC_RESPONSE = {
    "message": "Hello! I'm your monitoring system assistant. I can help you with:",
    "capabilities": [
        "Setting up monitoring rules and alerts",
        "Querying monitoring data and generating reports",
        "Creating charts and visualizations",
        "Analyzing system performance and violations"
    ],
    "suggestion": "Try asking me to 'Set a monitor' or 'Show me the current violations' to get started!",
    "examples": [
        "Set a monitor and alert me via email if API requests exceed 10 in 10 minutes",
        "Show me all currently violated rules",
        "Plot a chart of email notifications over time",
        "Give me a summary of recent violations"
    ]
}

# Monitoring Text Responses
MONITORING_TEXT_RESPONSES = {
    "violations": "Current system status: 3 active violations detected. API response time exceeded threshold at 14:30 (avg 250ms, threshold 200ms). Database connection pool usage at 85% (threshold 80%). Memory usage on server-2 at 92% (threshold 90%).",
    "performance": "System performance summary: Overall uptime 99.7% this month. Average API response time: 145ms. Database query performance: 95% under 100ms. Current active monitors: 12. Total alerts sent today: 7.",
    "rules": "Active monitoring rules: 12 total rules configured. 8 rules for API performance monitoring, 3 for database health checks, 1 for memory usage alerts. All rules are currently active and functioning normally.",
    "default": "Monitoring system overview: All systems operational. 12 active monitoring rules, 3 current violations, 99.7% uptime this month. Latest alert: High memory usage on server-2 at 15:45."
}

# Create Rule Response
CREATE_RULE_RESPONSE = "I can help you create a new monitoring rule. Here's what I've configured based on your request: A new monitoring rule has been created with the specified conditions. The system will now monitor the defined metrics and trigger alerts when thresholds are exceeded. You can modify this rule anytime through the monitoring dashboard."

# Table Data Configurations
TABLE_DATA = {
    "violations": {
        "headers": ["Rule Name", "Violation Time", "Current Value", "Threshold", "Status"],
        "rows": [
            ["API Response Time", "14:30", "250ms", "200ms", "VIOLATED"],
            ["DB Connection Pool", "14:25", "85%", "80%", "VIOLATED"],
            ["Memory Usage Server-2", "15:45", "92%", "90%", "VIOLATED"],
            ["Disk Space", "12:15", "65%", "80%", "OK"],
            ["CPU Usage", "15:30", "45%", "70%", "OK"]
        ]
    },
    "rules": {
        "headers": ["Rule ID", "Rule Name", "Type", "Threshold", "Alert Method", "Status"],
        "rows": [
            ["R001", "API Response Time", "Performance", "200ms", "Email", "Active"],
            ["R002", "Database Connections", "Resource", "80%", "Email + Slack", "Active"],
            ["R003", "Memory Usage", "Resource", "90%", "Email", "Active"],
            ["R004", "Disk Space", "Resource", "80%", "Email", "Active"],
            ["R005", "Error Rate", "Application", "5%", "PagerDuty", "Active"]
        ]
    },
    "monitoring_overview": {
        "headers": ["Metric", "Current Value", "Threshold", "Last Alert", "Status"],
        "rows": [
            ["API Response Time", "145ms", "200ms", "Never", "OK"],
            ["Database Connections", "65%", "80%", "2h ago", "OK"], 
            ["Memory Usage", "72%", "90%", "1h ago", "OK"],
            ["Error Rate", "2.1%", "5%", "Never", "OK"],
            ["Uptime", "99.7%", "99%", "Never", "OK"]
        ]
    },
    "fallback": {
        "headers": ["Metric", "Current Value", "Previous Period", "Change"],
        "rows": [
            ["Revenue", "$245,000", "$220,000", "+11.4%"],
            ["Costs", "$180,000", "$165,000", "+9.1%"],
            ["Profit", "$65,000", "$55,000", "+18.2%"],
            ["ROI", "26.5%", "25.0%", "+1.5%"]
        ]
    }
}

# Chart Data Configurations
CHART_DATA = {
    "notifications": {
        "chartType": "line",
        "labels": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
        "datasets": [
            {
                "label": "Email Notifications",
                "data": [2, 1, 5, 8, 12, 6],
                "borderColor": "blue"
            },
            {
                "label": "Slack Alerts", 
                "data": [1, 0, 3, 4, 7, 3],
                "borderColor": "green"
            }
        ],
        "options": {"responsive": True, "scales": {"y": {"beginAtZero": True}}}
    },
    "performance": {
        "chartType": "line",
        "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "datasets": [
            {
                "label": "API Response Time (ms)",
                "data": [145, 152, 138, 165, 189, 142, 134],
                "borderColor": "orange"
            },
            {
                "label": "Threshold (200ms)",
                "data": [200, 200, 200, 200, 200, 200, 200],
                "borderColor": "red"
            }
        ],
        "options": {"responsive": True, "scales": {"y": {"beginAtZero": True}}}
    },
    "alerts_today": {
        "chartType": "bar",
        "labels": ["API Alerts", "DB Alerts", "Memory Alerts", "Disk Alerts"],
        "datasets": [
            {
                "label": "Alert Count Today",
                "data": [3, 2, 1, 0],
                "borderColor": "red"
            }
        ],
        "options": {"responsive": True}
    },
    "fallback": {
        "chartType": "pie",
        "labels": ["Product A", "Product B", "Product C", "Product D"],
        "datasets": [
            {
                "label": "Market Share",
                "data": [35.5, 28.2, 22.1, 14.2],
                "borderColor": "purple"
            }
        ],
        "options": {"responsive": True}
    }
}

# Ollama Prompt Template
INTENT_CLASSIFICATION_PROMPT = """
Classify the following query into one of these intents:

1. "monitoring_details" - if the user wants to GET/RETRIEVE/VIEW existing monitoring data, rules, reports, violations, charts, or analytics
   Examples: "show me rules", "list all violations", "get monitoring data", "view status", "which monitor has most rules", "give me analytics", "what's the violation rate", "monitors with highest rule count"

2. "create_rule" - if the user wants to CREATE/ADD/CONFIGURE new monitoring rules or alerts
   Examples: "create a rule", "set up monitoring", "add an alert", "configure new monitor", "set up a new alert"

3. "generic_question" - if it's a general question about capabilities, help, what the system can do
   Examples: "what can you do?", "how does this work?", "help me understand"

Query: "{query}"

IMPORTANT: Analytics queries asking "which", "what", "how many", "most", "highest", "average" are ALWAYS "monitoring_details" because they retrieve existing data.

Focus on the ACTION: Is the user asking to RETRIEVE existing data or CREATE something new?

Respond with only one word: monitoring_details, create_rule, or generic_question
"""
