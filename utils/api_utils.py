"""
Utility functions for API connections and common operations.

This module provides reusable functions for:
- Creating API clients with appropriate configurations
- Testing connections to different API providers (OpenAI, Ollama)
- Handling common API errors
"""

import os
import logging
import traceback
import time
from enum import Enum
from typing import Optional, Dict, Any, Union, Tuple, List
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

setup_env_path = Path(__file__).parent.parent / "setup" / ".env"
if setup_env_path.exists():
    load_dotenv(setup_env_path)
else:
    load_dotenv()

logger = logging.getLogger(__name__)

class APIProvider(str, Enum):
    """Enum for API providers"""
    OPENAI = "openai"
    OLLAMA = "ollama"

class ConnectionStatus:
    """Class to track API connection status"""
    def __init__(self):
        self.status: Dict[str, Dict[str, Any]] = {}
        
    def update_status(self, provider: str, success: bool, base_url: Optional[str] = None, 
                     error: Optional[str] = None, timestamp: Optional[float] = None):
        """Update the status of a connection"""
        if timestamp is None:
            timestamp = time.time()
            
        self.status[provider] = {
            "success": success,
            "base_url": base_url,
            "error": error,
            "timestamp": timestamp,
            "last_checked": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        }
    
    def get_status(self, provider: str) -> Dict[str, Any]:
        """Get the status of a connection"""
        return self.status.get(provider, {
            "success": False,
            "base_url": None,
            "error": "Never checked",
            "timestamp": 0,
            "last_checked": "Never"
        })
    
    def is_connected(self, provider: str) -> bool:
        """Check if a provider is connected"""
        return self.get_status(provider).get("success", False)
    
    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get all connection statuses"""
        return self.status

connection_status = ConnectionStatus()

def create_client(
    api_provider: APIProvider,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> OpenAI:
    """
    Create an API client for the specified provider.
    
    Args:
        api_provider: Which API provider to use (openai or ollama)
        api_key: API key for the provider (OpenAI API key or "ollama" for Ollama)
        base_url: Base URL for the API (required for Ollama)
        
    Returns:
        OpenAI client configured for the specified provider
    """
    if api_key is None and api_provider == APIProvider.OPENAI:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if api_provider == APIProvider.OLLAMA:
        if not base_url:
            base_url = "http://localhost:11434/v1/"
            
        client = OpenAI(
            base_url=base_url,
            api_key=api_key or "ollama"
        )
    else:
        client = OpenAI(api_key=api_key)
    
    return client

def test_connection(
    client: OpenAI,
    api_provider: APIProvider,
    base_url: Optional[str] = None,
    update_status: bool = True
) -> bool:
    """
    Test the connection to the API.
    
    Args:
        client: The OpenAI client to test
        api_provider: Which API provider is being tested
        base_url: Base URL for the API (used for logging)
        update_status: Whether to update the global connection status
        
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        client.models.list()
        logger.info(f"Successfully connected to {api_provider} API")
        
        if api_provider == APIProvider.OLLAMA and base_url:
            logger.info(f"Using Ollama API at {base_url}")
        
        if update_status:
            connection_status.update_status(api_provider.value, True, base_url)
            
        return True
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error connecting to {api_provider} API: {error_msg}")
        logger.debug(traceback.format_exc())
        
        if update_status:
            connection_status.update_status(api_provider.value, False, base_url, error_msg)
            
        return False

def get_api_client(
    api_provider: APIProvider,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    test: bool = True
) -> Union[OpenAI, None]:
    """
    Create and test an API client for the specified provider.
    
    Args:
        api_provider: Which API provider to use (openai or ollama)
        api_key: API key for the provider (OpenAI API key or "ollama" for Ollama)
        base_url: Base URL for the API (required for Ollama)
        test: Whether to test the connection after creating the client
        
    Returns:
        OpenAI client if successful, None if connection test fails
    """
    client = create_client(api_provider, api_key, base_url)
    
    if test and not test_connection(client, api_provider, base_url):
        logger.warning(f"Connection test failed for {api_provider} API")
        return None
        
    return client

def test_all_connections() -> Dict[str, bool]:
    """
    Test connections to all configured API providers.
    
    Returns:
        Dictionary mapping provider names to connection status (True/False)
    """
    results = {}
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        client = create_client(APIProvider.OPENAI, openai_api_key)
        results[APIProvider.OPENAI.value] = test_connection(client, APIProvider.OPENAI)
    else:
        logger.warning("OpenAI API key not found, skipping connection test")
        connection_status.update_status(APIProvider.OPENAI.value, False, None, "API key not found")
        results[APIProvider.OPENAI.value] = False
    
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1/")
    client = create_client(APIProvider.OLLAMA, base_url=ollama_base_url)
    results[APIProvider.OLLAMA.value] = test_connection(client, APIProvider.OLLAMA, ollama_base_url)
    
    return results

def get_connection_status() -> Dict[str, Dict[str, Any]]:
    """
    Get the status of all API connections.
    
    Returns:
        Dictionary with connection status details for all providers
    """
    return connection_status.get_all_statuses()

def is_connected(provider: APIProvider) -> bool:
    """
    Check if a specific provider is connected.
    
    Args:
        provider: The API provider to check
        
    Returns:
        True if connected, False otherwise
    """
    return connection_status.is_connected(provider.value)

def get_available_models(client: OpenAI) -> List[str]:
    """
    Get a list of available models from the API.
    
    Args:
        client: The OpenAI client to use
        
    Returns:
        List of model IDs
    """
    try:
        models = client.models.list()
        return [model.id for model in models.data]
    except Exception as e:
        logger.error(f"Error getting available models: {str(e)}")
        return [] 