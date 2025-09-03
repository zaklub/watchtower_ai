"""
Ollama client for intent classification
"""

import sys
import os
import httpx
from typing import Optional

# Import for LangChain integration
try:
    from langchain_ollama import OllamaLLM
except ImportError:
    OllamaLLM = None

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import OLLAMA_CONFIG


class OllamaClient:
    """
    Client for communicating with Ollama API
    """
    
    def __init__(self):
        self.base_url = OLLAMA_CONFIG["base_url"]
        self.model = OLLAMA_CONFIG["model"]
        self.timeout = OLLAMA_CONFIG["timeout"]
        
    async def classify_intent(self, prompt: str) -> Optional[str]:
        """
        Send a prompt to Ollama for intent classification
        
        Args:
            prompt: The formatted prompt to send to Ollama
            
        Returns:
            Optional[str]: The raw response from Ollama, or None if failed
        """
        
        print(f"🤖 Starting Ollama intent classification")
        print(f"📡 Ollama URL: {self.base_url}")
        print(f"🧠 Model: {self.model}")
        print(f"📝 Prompt created, length: {len(prompt)} characters")

        try:
            print("🚀 Attempting to connect to Ollama...")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                print(f"⏱️ Sending request to Ollama with timeout: {self.timeout}s")
                
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                
                print(f"📨 Ollama response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    raw_response = result.get("response", "")
                    
                    print(f"✅ Ollama raw response: '{raw_response}'")
                    return raw_response
                else:
                    print(f"❌ Ollama request failed with status {response.status_code}")
                    try:
                        error_detail = response.text
                        print(f"📋 Error details: {error_detail}")
                    except:
                        print("📋 No error details available")
                    
                    return None
                    
        except Exception as e:
            print(f"💥 Exception calling Ollama: {type(e).__name__}: {e}")
            # Re-raise connection errors so they can be handled by retry logic
            raise
    
    async def health_check(self) -> bool:
        """
        Check if Ollama is available and responding
        
        Returns:
            bool: True if Ollama is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    def get_config(self) -> dict:
        """
        Get current Ollama configuration
        
        Returns:
            dict: Current configuration settings
        """
        return {
            "base_url": self.base_url,
            "model": self.model,
            "timeout": self.timeout
        }
    
    def get_langchain_llm(self):
        """
        Get a LangChain-compatible LLM instance for use with agents
        
        Returns:
            OllamaLLM: LangChain Ollama LLM instance
        """
        if OllamaLLM is None:
            raise ImportError("langchain_ollama is required for LangChain integration. Install with: pip install langchain-ollama")
        
        return OllamaLLM(
            base_url=self.base_url,
            model=self.model,
            timeout=self.timeout
        )
