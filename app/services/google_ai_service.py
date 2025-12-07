"""Google AI Studio service for LLM interactions"""
import os
import time
import google.generativeai as genai
from typing import Optional, List, Dict, Any
from fastapi import HTTPException


class GoogleAIService:
    """Service for interacting with Google AI Studio (Gemini)"""
    
    def __init__(self):
        api_key = os.getenv("GOOGLE_AI_API_KEY")
        if not api_key:
            self.available = False
            self.error = "GOOGLE_AI_API_KEY environment variable is not set"
            return
        
        try:
            genai.configure(api_key=api_key)
            model_name = os.getenv("GOOGLE_AI_MODEL", "gemini-pro")
            # Strip "models/" prefix if present (some configs include it)
            if model_name.startswith("models/"):
                model_name = model_name.replace("models/", "", 1)
            self.model_name = model_name
            # Fallback models to try if primary model hits quota
            fallback_models_str = os.getenv("GOOGLE_AI_FALLBACK_MODELS", "gemini-2.5-flash,gemini-2.0-flash")
            self.fallback_models = [m.strip() for m in fallback_models_str.split(",") if m.strip()]
            self.available = True
            self.error = None
        except Exception as e:
            self.available = False
            self.error = str(e)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_output_tokens: int = 2048
    ) -> str:
        """
        Call Google AI chat API
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (default: uses default_model)
            temperature: Temperature for generation
            max_output_tokens: Max tokens to generate
        
        Returns:
            str: Response text
        """
        if not self.available:
            error_msg = "Google AI service is not available."
            if self.error:
                error_msg += f" Error: {self.error}"
            raise HTTPException(
                status_code=503,
                detail=error_msg
            )
        
        try:
            model_name = model or self.model_name
            # Strip "models/" prefix if present
            if model_name.startswith("models/"):
                model_name = model_name.replace("models/", "", 1)
            genai_model = genai.GenerativeModel(model_name)
            
            # Build prompt from messages
            # Google AI uses a different format - combine system and user messages
            prompt_parts = []
            for msg in messages:
                if msg["role"] == "system":
                    prompt_parts.append(f"System Instructions: {msg['content']}")
                elif msg["role"] == "user":
                    prompt_parts.append(f"User: {msg['content']}")
                elif msg["role"] == "assistant":
                    prompt_parts.append(f"Assistant: {msg['content']}")
            
            full_prompt = "\n\n".join(prompt_parts)
            
            # Generate content
            # Pass generation config as keyword arguments
            response = genai_model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_output_tokens,
                }
            )
            
            if not response:
                raise HTTPException(
                    status_code=500,
                    detail="Invalid response from Google AI API"
                )
            
            # Extract text from response
            # Google Generative AI returns response with candidates[].content.parts[]
            text_parts = []
            
            # Method 1: Try simple text accessor (works for simple single-part responses)
            try:
                return response.text
            except ValueError:
                # response.text doesn't work, need to extract from parts
                pass
            
            # Method 2: Extract from candidates -> content -> parts (standard way)
            if hasattr(response, 'candidates') and response.candidates:
                # First check prompt_feedback for blocking reasons
                if hasattr(response, 'prompt_feedback'):
                    feedback = response.prompt_feedback
                    if hasattr(feedback, 'block_reason') and feedback.block_reason:
                        block_reasons = {
                            0: "BLOCK_REASON_UNSPECIFIED",
                            1: "SAFETY",
                            2: "OTHER"
                        }
                        reason = block_reasons.get(feedback.block_reason, f"UNKNOWN({feedback.block_reason})")
                        safety_msg = ""
                        if hasattr(feedback, 'safety_ratings') and feedback.safety_ratings:
                            blocked_categories = []
                            for rating in feedback.safety_ratings:
                                if hasattr(rating, 'blocked') and rating.blocked:
                                    if hasattr(rating, 'category'):
                                        blocked_categories.append(str(rating.category))
                            if blocked_categories:
                                safety_msg = f" Categories: {', '.join(blocked_categories)}"
                        raise HTTPException(
                            status_code=400,
                            detail=f"Google AI blocked the prompt. Reason: {reason}.{safety_msg}"
                        )
                
                for candidate in response.candidates:
                    # Check for finish_reason and safety issues
                    finish_reason = None
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = candidate.finish_reason
                        if finish_reason and finish_reason != 1:  # 1 = STOP (normal finish)
                            # MAX_TOKENS (2) means response was truncated but we can still use it
                            if finish_reason == 2:  # MAX_TOKENS
                                # Don't raise error, just continue to extract text
                                # The response may still be usable
                                pass
                            elif finish_reason == 3:  # SAFETY
                                # Check for safety ratings
                                safety_msg = ""
                                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                                    blocked_categories = []
                                    for rating in candidate.safety_ratings:
                                        if hasattr(rating, 'blocked') and rating.blocked:
                                            if hasattr(rating, 'category'):
                                                blocked_categories.append(str(rating.category))
                                    if blocked_categories:
                                        safety_msg = f" Content blocked by safety filters: {', '.join(blocked_categories)}"
                                
                                finish_reasons = {
                                    0: "FINISH_REASON_UNSPECIFIED",
                                    1: "STOP",
                                    2: "MAX_TOKENS",
                                    3: "SAFETY",
                                    4: "RECITATION",
                                    5: "OTHER"
                                }
                                reason_name = finish_reasons.get(finish_reason, f"UNKNOWN({finish_reason})")
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Google AI response finished with reason: {reason_name}.{safety_msg}"
                                )
                            else:
                                # Other finish reasons (RECITATION, OTHER, etc.)
                                finish_reasons = {
                                    0: "FINISH_REASON_UNSPECIFIED",
                                    1: "STOP",
                                    2: "MAX_TOKENS",
                                    3: "SAFETY",
                                    4: "RECITATION",
                                    5: "OTHER"
                                }
                                reason_name = finish_reasons.get(finish_reason, f"UNKNOWN({finish_reason})")
                                # For non-critical reasons, try to extract text anyway
                                if finish_reason == 4:  # RECITATION - might still have usable content
                                    pass
                                else:
                                    raise HTTPException(
                                        status_code=400,
                                        detail=f"Google AI response finished with reason: {reason_name}"
                                    )
                    
                    if hasattr(candidate, 'content'):
                        content = candidate.content
                        if content:
                            # Try to get parts
                            if hasattr(content, 'parts'):
                                if not content.parts or len(content.parts) == 0:
                                    # No parts, but check if there's text directly in content
                                    if hasattr(content, 'text'):
                                        text_parts.append(str(content.text))
                                    else:
                                        # Check finish_reason to provide better error message
                                        if finish_reason == 3:  # SAFETY
                                            raise HTTPException(
                                                status_code=400,
                                                detail="Google AI blocked the response due to safety filters."
                                            )
                                        elif finish_reason == 2:  # MAX_TOKENS
                                            # MAX_TOKENS but no parts - try to continue anyway
                                            # Sometimes response is still usable even if truncated
                                            # Don't raise error immediately, let it continue to try other extraction methods
                                            pass
                                        else:
                                            raise HTTPException(
                                                status_code=500,
                                                detail=f"Google AI response has no content parts. Finish reason: {finish_reason if finish_reason else 'unknown'}"
                                            )
                                else:
                                    # Has parts, extract text
                                    for part in content.parts:
                                        # Part can be a Text object with .text attribute
                                        if hasattr(part, 'text'):
                                            text_parts.append(str(part.text))
                                        # Or it might be a string directly
                                        elif isinstance(part, str):
                                            text_parts.append(part)
                                        # Try to convert part to string if possible
                                        else:
                                            try:
                                                text_parts.append(str(part))
                                            except:
                                                pass
                            # If no parts attribute, try to get text directly
                            elif hasattr(content, 'text'):
                                text_parts.append(str(content.text))
                            else:
                                # No parts and no text - check if it's a dict-like structure
                                if isinstance(content, dict):
                                    if 'text' in content:
                                        text_parts.append(str(content['text']))
                                    elif 'parts' in content and content['parts']:
                                        for part in content['parts']:
                                            if isinstance(part, dict) and 'text' in part:
                                                text_parts.append(str(part['text']))
                                            elif isinstance(part, str):
                                                text_parts.append(part)
            
            if text_parts:
                return ''.join(text_parts)
            
            # Method 3: Try accessing response.parts directly (alternative structure)
            if hasattr(response, 'parts'):
                for part in response.parts:
                    if hasattr(part, 'text'):
                        text_parts.append(part.text)
                    elif isinstance(part, str):
                        text_parts.append(part)
            
            if text_parts:
                return ''.join(text_parts)
            
            # If still no text, provide detailed error for debugging
            error_details = []
            error_details.append(f"Response type: {type(response).__name__}")
            if hasattr(response, 'candidates'):
                error_details.append(f"Candidates: {len(response.candidates) if response.candidates else 0}")
                if response.candidates:
                    candidate = response.candidates[0]
                    error_details.append(f"First candidate type: {type(candidate).__name__}")
                    if hasattr(candidate, 'content'):
                        error_details.append(f"Content type: {type(candidate.content).__name__}")
                        if hasattr(candidate.content, 'parts'):
                            error_details.append(f"Parts count: {len(candidate.content.parts) if candidate.content.parts else 0}")
            
            raise HTTPException(
                status_code=500,
                detail=f"Could not extract text from Google AI API response. {' | '.join(error_details)}"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            error_str = str(e)
            
            # Check for quota/rate limit errors (429)
            if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
                # Try fallback models if available
                models_to_try = [model_name]
                if hasattr(self, 'fallback_models'):
                    models_to_try.extend(self.fallback_models)
                
                # Remove duplicates while preserving order
                seen = set()
                models_to_try = [m for m in models_to_try if m not in seen and not seen.add(m)]
                
                # Try each model
                last_error = error_str
                for fallback_model in models_to_try:
                    if fallback_model == model_name:
                        continue  # Already tried the primary model
                    
                    try:
                        # Strip "models/" prefix if present
                        if fallback_model.startswith("models/"):
                            fallback_model = fallback_model.replace("models/", "", 1)
                        
                        genai_model = genai.GenerativeModel(fallback_model)
                        response = genai_model.generate_content(
                            full_prompt,
                            generation_config={
                                "temperature": temperature,
                                "max_output_tokens": max_output_tokens,
                            }
                        )
                        
                        # If we get here, fallback worked - extract response
                        if not response:
                            continue
                        
                        # Extract text (reuse the same extraction logic)
                        try:
                            return response.text
                        except ValueError:
                            pass
                        
                        # Method 2: Extract from candidates -> content -> parts
                        if hasattr(response, 'candidates') and response.candidates:
                            for candidate in response.candidates:
                                if hasattr(candidate, 'content'):
                                    content = candidate.content
                                    if content:
                                        if hasattr(content, 'parts') and content.parts:
                                            text_parts = []
                                            for part in content.parts:
                                                if hasattr(part, 'text'):
                                                    text_parts.append(str(part.text))
                                                elif isinstance(part, str):
                                                    text_parts.append(part)
                                            if text_parts:
                                                return ''.join(text_parts)
                                        elif hasattr(content, 'text'):
                                            return str(content.text)
                        
                        # If we got a response but couldn't extract text, continue to next model
                        continue
                        
                    except Exception as fallback_error:
                        last_error = str(fallback_error)
                        continue
                
                # All models failed, return detailed error
                raise HTTPException(
                    status_code=429,
                    detail=f"Quota exceeded for all models. Primary model: {model_name}. Tried fallbacks: {', '.join(self.fallback_models) if hasattr(self, 'fallback_models') else 'none'}. Original error: {error_str}. Please wait and retry, or check your Google AI API quota at https://ai.dev/usage"
                )
            
            # For other errors, return as before
            raise HTTPException(
                status_code=503,
                detail=f"Error calling Google AI API: {error_str}"
            )
    
    def generate(
        self,
        system_message: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_output_tokens: int = 2048,
        model: Optional[str] = None
    ) -> str:
        """
        Generate text using Google AI
        
        Args:
            system_message: System message for the LLM
            user_prompt: User prompt/instruction
            temperature: Temperature for generation
            max_output_tokens: Max tokens to generate
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
            max_output_tokens=max_output_tokens
        )
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List all available Google AI models
        
        Returns:
            List[Dict]: List of model information dictionaries
        """
        if not self.available:
            error_msg = "Google AI service is not available."
            if self.error:
                error_msg += f" Error: {self.error}"
            raise HTTPException(
                status_code=503,
                detail=error_msg
            )
        
        try:
            models = genai.list_models()
            model_list = []
            
            for model in models:
                # Extract model information
                model_info = {
                    "name": model.name,
                    "display_name": getattr(model, 'display_name', model.name),
                    "description": getattr(model, 'description', ''),
                    "supported_generation_methods": getattr(model, 'supported_generation_methods', []),
                    "input_token_limit": getattr(model, 'input_token_limit', None),
                    "output_token_limit": getattr(model, 'output_token_limit', None),
                }
                
                # Check if model supports generateContent
                if 'generateContent' in model_info['supported_generation_methods']:
                    model_list.append(model_info)
            
            return model_list
            
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Error listing Google AI models: {str(e)}"
            )


# Global instance
google_ai_service = GoogleAIService()

