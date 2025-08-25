"""
Intent classification module for Watchtower AI API
Contains intent classification logic using Ollama and fallback methods
"""

from .classify_intent import classify_intent
from .fallback_intent_classification import fallback_intent_classification

__all__ = [
    'classify_intent',
    'fallback_intent_classification'
]
