"""
Response Formatting Functions
Handles formatting of data for different response types (chart, text, table)
"""


def format_chart_response(data_records: list, query_description: str) -> dict:
    """Format data for time series line chart visualization."""
    if not data_records:
        return {
            "labels": [],
            "datasets": []
        }
    
    # Find timestamp field in the records
    timestamp_field = None
    for key in data_records[0].keys():
        if any(time_key in key.lower() for time_key in ['timestamp', 'time', 'date', 'created', 'start_time', 'end_time']):
            timestamp_field = key
            break
    
    if not timestamp_field:
        # If no timestamp field found, return empty chart
        return {
            "labels": [],
            "datasets": []
        }
    
    # Extract and process timestamp data
    time_data = {}
    for record in data_records:
        timestamp_value = record.get(timestamp_field)
        if timestamp_value:
            # Convert timestamp to date string (YYYY-MM-DD format)
            try:
                if isinstance(timestamp_value, str):
                    # Handle different timestamp formats
                    if 'T' in timestamp_value:
                        # ISO format: "2025-08-13T16:12:25.180000"
                        date_str = timestamp_value.split('T')[0]
                    elif ' ' in timestamp_value:
                        # SQL format: "2025-08-13 16:12:25.180000"
                        date_str = timestamp_value.split(' ')[0]
                    else:
                        date_str = timestamp_value[:10]  # Take first 10 characters
                else:
                    # If it's already a date object
                    date_str = str(timestamp_value)[:10]
                
                # Count occurrences per date
                time_data[date_str] = time_data.get(date_str, 0) + 1
            except Exception:
                continue
    
    # Sort by date and create labels and datasets
    sorted_dates = sorted(time_data.keys())
    labels = sorted_dates
    datasets = [time_data[date] for date in sorted_dates]
    
    return {
        "labels": labels,
        "datasets": datasets
    }


def format_text_response(data_records: list, query_description: str) -> dict:
    """Format data as a text summary."""
    if not data_records:
        return {
            "message": f"No {query_description} found."
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
        "message": " ".join(summary_parts)
    }
