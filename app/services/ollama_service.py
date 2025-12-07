"""Ollama service for LLM interactions"""
import os
import ollama
from typing import Optional, List, Dict
from fastapi import HTTPException


class OllamaService:
    """Service for interacting with Ollama LLM"""
    
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.default_model = os.getenv("OLLAMA_MODEL", "llama3.1:latest")
        self.client = None
        self.available = False
        self.error = None
        self._check_connection()
    
    def _check_connection(self):
        """Check and update Ollama connection status"""
        try:
            if self.client is None:
                self.client = ollama.Client(host=self.base_url)
            
            # Test connection
            self.client.list()
            self.available = True
            self.error = None
            return True
        except Exception as e:
            self.available = False
            self.error = str(e)
            return False
    
    def reconnect(self):
        """Manually retry Ollama connection"""
        return self._check_connection()
    
    def _get_available_models(self):
        """Get list of available Ollama models"""
        try:
            if self.client:
                models = self.client.list()
                if models and "models" in models:
                    return [m.get("name", "unknown") for m in models["models"]]
                return ["Unable to list models"]
        except:
            pass
        return ["Unable to retrieve models"]
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        num_predict: int = 500
    ) -> str:
        """
        Call Ollama chat API
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (default: uses default_model)
            temperature: Temperature for generation
            num_predict: Max tokens to predict
        
        Returns:
            str: Response text
        """
        # Retry connection check before processing
        if not self.available:
            self._check_connection()
        
        if not self.available:
            error_msg = "Ollama service is not available. Please ensure Ollama server is running."
            if self.error:
                error_msg += f" Error: {self.error}"
            error_msg += f" Ollama URL: {self.base_url}"
            raise HTTPException(
                status_code=503,
                detail=error_msg
            )
        
        model_name = model or self.default_model
        
        try:
            response = self.client.chat(
                model=model_name,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": num_predict
                }
            )
        except Exception as ollama_error:
            # Check if it's a model not found error
            error_str = str(ollama_error).lower()
            if "model" in error_str and ("not found" in error_str or "does not exist" in error_str):
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{model_name}' not found. Available models: {self._get_available_models()}. Please pull the model using: ollama pull {model_name}"
                )
            raise HTTPException(
                status_code=503,
                detail=f"Error calling Ollama API: {str(ollama_error)}"
            )
        
        if not response or "message" not in response:
            raise HTTPException(
                status_code=500,
                detail="Invalid response from Ollama API"
            )
        
        return response["message"]["content"]
    
    def generate(
        self,
        system_message: str,
        user_prompt: str,
        temperature: float = 0.7,
        num_predict: int = 2000,
        model: Optional[str] = None
    ) -> str:
        """
        Generate text using Ollama
        
        Args:
            system_message: System message for the LLM
            user_prompt: User prompt/instruction
            temperature: Temperature for generation
            num_predict: Max tokens to predict
            model: Model name (default: uses default_model)
        
        Returns:
            str: Generated text
        """
        messages = [
            {"role": "system", "content": f"{system_message} Return valid JSON only."},
            {"role": "user", "content": user_prompt}
        ]
        
        return self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            num_predict=num_predict
        )


# Global instance
ollama_service = OllamaService()

