"""
Fallback intent classification logic using keyword matching
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import INTENT_KEYWORDS


def fallback_intent_classification(query: str) -> str:
    """
    Fallback intent classification using keyword matching from config
    
    Args:
        query: The user's query string
        
    Returns:
        str: The classified intent based on keyword matching
    """
    print(f"🔤 Using fallback classification for: '{query}'")
    query_lower = query.lower()
    
    # Create rule keywords
    create_matches = [kw for kw in INTENT_KEYWORDS["create_rule"] if kw in query_lower]
    if create_matches:
        print(f"✅ Found 'create_rule' keywords: {create_matches}")
        return "create_rule"
    
    # Monitoring details keywords
    monitoring_matches = [kw for kw in INTENT_KEYWORDS["monitoring_details"] if kw in query_lower]
    if monitoring_matches:
        print(f"✅ Found 'monitoring_details' keywords: {monitoring_matches}")
        return "monitoring_details"
    
    # Default to generic
    print("ℹ️ No keywords matched, defaulting to 'generic_question'")
    return "generic_question"
