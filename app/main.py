from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import ollama
import json
import os
import re

app = FastAPI(title="Llama Service", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str


class ChatPayload(BaseModel):
    model: str
    messages: List[Message]
    format: Optional[dict] = None


# Ollama client configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:latest")

# Initialize Ollama client
ollama_client = None
ollama_available = False
ollama_error = None


def _get_available_models():
    """Get list of available Ollama models"""
    try:
        if ollama_client:
            models = ollama_client.list()
            if models and "models" in models:
                return [m.get("name", "unknown") for m in models["models"]]
            return ["Unable to list models"]
    except:
        pass
    return ["Unable to retrieve models"]


def check_ollama_connection():
    """Check and update Ollama connection status. Can be called to retry connection."""
    global ollama_client, ollama_available, ollama_error
    
    try:
        # Reinitialize client if needed
        if ollama_client is None:
            ollama_client = ollama.Client(host=OLLAMA_BASE_URL)
        
        # Test connection
        ollama_client.list()
        ollama_available = True
        ollama_error = None
        return True
    except Exception as e:
        ollama_available = False
        ollama_error = str(e)
        return False


# Initial connection check
check_ollama_connection()


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "llama",
        "version": "1.0.0",
        "ollama_available": ollama_available,
        "ollama_url": OLLAMA_BASE_URL,
        "default_model": OLLAMA_MODEL,
        "ollama_error": ollama_error if not ollama_available else None
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy" if ollama_available else "degraded",
        "service": "llama",
        "version": "1.0.0",
        "ollama_available": ollama_available
    }


@app.post("/reconnect")
async def reconnect():
    """Manually retry Ollama connection"""
    success = check_ollama_connection()
    return {
        "success": success,
        "ollama_available": ollama_available,
        "ollama_url": OLLAMA_BASE_URL,
        "error": ollama_error if not success else None
    }


@app.get("/info")
async def info():
    """Get service information"""
    return {
        "service": "Llama IELTS Scoring Service",
        "version": "1.0.0",
        "description": "IELTS speaking scoring using Ollama LLM",
        "ollama_available": ollama_available,
        "ollama_url": OLLAMA_BASE_URL,
        "default_model": OLLAMA_MODEL,
        "endpoints": {
            "health": "GET /health",
            "info": "GET /info",
            "score": "POST /api/score (simplified scoring endpoint)",
            "chat": "POST /api/chat (advanced chat endpoint)"
        },
        "note": "Requires Ollama server running with a compatible model (e.g., llama3.1:8b)"
    }


def build_ielts_prompt(transcription: str, question_text: str, topic: str, level: str) -> str:
    """Build prompt for IELTS scoring"""
    question_section = ""
    if question_text:
        question_section = f"""Question:
{question_text}

"""
    
    relevance_warning = ""
    if question_text:
        relevance_warning = """
IMPORTANT: First check if the student's response is relevant to the question asked. If the response does not answer the question or is about a completely different topic, you MUST significantly penalize the scores, especially:
- Band Score: Reduce by 2-3 points if completely off-topic
- Fluency Score: Reduce significantly as the response lacks coherence with the question
- Vocabulary Score: May be less relevant if off-topic
- Grammar Score: Can still be evaluated but overall band should reflect irrelevance

If the response is off-topic, mention this clearly in the overallFeedback.

"""
    
    return f"""You are an expert IELTS speaking examiner. Evaluate the following speaking response.

Topic: {topic}
Target Level: {level}

{question_section}Student's Response:
{transcription}

{relevance_warning}Please provide a detailed evaluation in the following JSON format:
{{
    "bandScore": <decimal 0-9>,
    "pronunciationScore": <decimal 0-9>,
    "grammarScore": <decimal 0-9>,
    "vocabularyScore": <decimal 0-9>,
    "fluencyScore": <decimal 0-9>,
    "overallFeedback": "<detailed feedback paragraph explaining strengths and areas for improvement. If the response is off-topic, clearly state this and explain why the scores are reduced.>"
}}

Evaluation Criteria:
- Band Score: Overall IELTS band score (0-9). MUST be significantly reduced if response is off-topic or doesn't answer the question.
- Pronunciation: Clarity, intonation, stress patterns
- Grammar: Accuracy, range, complexity
- Vocabulary: Range, precision, collocations (relevance to question matters)
- Fluency: Coherence, hesitation, natural flow (coherence with question is critical)

Return ONLY valid JSON, no additional text."""


def extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response"""
    # Try to find JSON in the response
    json_match = re.search(r'\{[^{}]*"bandScore"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except:
            pass
    
    # Try to parse entire response as JSON
    try:
        return json.loads(text)
    except:
        pass
    
    # Fallback: try to extract values using regex
    result = {}
    patterns = {
        "bandScore": r'"bandScore"\s*:\s*([0-9.]+)',
        "pronunciationScore": r'"pronunciationScore"\s*:\s*([0-9.]+)',
        "grammarScore": r'"grammarScore"\s*:\s*([0-9.]+)',
        "vocabularyScore": r'"vocabularyScore"\s*:\s*([0-9.]+)',
        "fluencyScore": r'"fluencyScore"\s*:\s*([0-9.]+)',
        "overallFeedback": r'"overallFeedback"\s*:\s*"([^"]+)"'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            if key == "overallFeedback":
                result[key] = match.group(1)
            else:
                result[key] = float(match.group(1))
    
    return result


class ScoreRequest(BaseModel):
    """Request model for direct scoring endpoint"""
    transcription: str
    questionText: Optional[str] = None
    topic: Optional[str] = "General"
    level: Optional[str] = "intermediate"


@app.post("/api/score")
async def score(request: ScoreRequest):
    """
    Score IELTS speaking response directly
    
    Simplified endpoint that takes transcription, topic, and level directly.
    
    **Request body:**
    ```json
    {
        "transcription": "The student's speaking response text...",
        "topic": "Education",
        "level": "intermediate"
    }
    ```
    
    **Response:**
    ```json
    {
        "bandScore": 6.5,
        "pronunciationScore": 6.0,
        "grammarScore": 6.5,
        "vocabularyScore": 6.0,
        "fluencyScore": 6.5,
        "overallFeedback": "Detailed feedback..."
    }
    ```
    """
    # Retry connection check before processing
    if not ollama_available:
        check_ollama_connection()
    
    if not ollama_available:
        error_msg = "Ollama service is not available. Please ensure Ollama server is running."
        if ollama_error:
            error_msg += f" Error: {ollama_error}"
        error_msg += f" Ollama URL: {OLLAMA_BASE_URL}"
        raise HTTPException(
            status_code=503,
            detail=error_msg
        )
    
    try:
        # Build IELTS-specific prompt
        prompt = build_ielts_prompt(
            request.transcription,
            request.questionText or "",
            request.topic or "General",
            request.level or "intermediate"
        )
        
        messages = [
            {"role": "system", "content": "You are an expert IELTS speaking examiner. Always return valid JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        # Call Ollama
        model = OLLAMA_MODEL
        try:
            response = ollama_client.chat(
                model=model,
                messages=messages,
                options={
                    "temperature": 0.3,  # Lower temperature for more consistent scoring
                    "num_predict": 500
                }
            )
        except Exception as ollama_error:
            # Check if it's a model not found error
            error_str = str(ollama_error).lower()
            if "model" in error_str and ("not found" in error_str or "does not exist" in error_str):
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{model}' not found. Available models: {_get_available_models()}. Please pull the model using: ollama pull {model}"
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
        
        response_text = response["message"]["content"]
        
        # Extract JSON from response
        result = extract_json_from_response(response_text)
        
        # Validate and set defaults
        band_score = float(result.get("bandScore", 6.5))
        pronunciation_score = float(result.get("pronunciationScore", 6.0))
        grammar_score = float(result.get("grammarScore", 6.5))
        vocabulary_score = float(result.get("vocabularyScore", 6.0))
        fluency_score = float(result.get("fluencyScore", 6.5))
        overall_feedback = result.get("overallFeedback", "Evaluation completed.")
        
        # Clamp scores to valid range
        def clamp_score(score):
            return max(0.0, min(9.0, float(score)))
        
        return {
            "bandScore": clamp_score(band_score),
            "pronunciationScore": clamp_score(pronunciation_score),
            "grammarScore": clamp_score(grammar_score),
            "vocabularyScore": clamp_score(vocabulary_score),
            "fluencyScore": clamp_score(fluency_score),
            "overallFeedback": overall_feedback
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing scoring request: {str(e)}"
        )


@app.post("/api/chat")
async def chat(payload: ChatPayload):
    """
    Score IELTS speaking response using Ollama LLM
    
    Expected payload format:
    {
        "model": "llama3.1",
        "messages": [
            {
                "role": "system",
                "content": "You are an IELTS speaking examiner..."
            },
            {
                "role": "user",
                "content": "Evaluate this response: ..."
            }
        ]
    }
    """
    # Retry connection check before processing
    if not ollama_available:
        check_ollama_connection()
    
    if not ollama_available:
        error_msg = "Ollama service is not available. Please ensure Ollama server is running."
        if ollama_error:
            error_msg += f" Error: {ollama_error}"
        error_msg += f" Ollama URL: {OLLAMA_BASE_URL}"
        raise HTTPException(
            status_code=503,
            detail=error_msg
        )
    
    try:
        # Extract transcription, topic, and level from messages
        user_message = None
        system_message = None
        
        for msg in payload.messages:
            if msg.role == "user":
                user_message = msg.content
            elif msg.role == "system":
                system_message = msg.content
        
        # If no explicit prompt, build one from transcription
        if not system_message or "IELTS" not in system_message:
            # Try to extract transcription from user message
            transcription = user_message or ""
            topic = "General"
            level = "intermediate"
            
            # Build IELTS-specific prompt
            prompt = build_ielts_prompt(transcription, topic, level)
            messages = [
                {"role": "system", "content": "You are an expert IELTS speaking examiner. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ]
        else:
            # Use provided messages
            messages = [{"role": msg.role, "content": msg.content} for msg in payload.messages]
        
        # Call Ollama
        model = payload.model or OLLAMA_MODEL
        try:
            response = ollama_client.chat(
                model=model,
                messages=messages,
                options={
                    "temperature": 0.3,  # Lower temperature for more consistent scoring
                    "num_predict": 500
                }
            )
        except Exception as ollama_error:
            # Check if it's a model not found error
            error_str = str(ollama_error).lower()
            if "model" in error_str and ("not found" in error_str or "does not exist" in error_str):
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{model}' not found. Available models: {_get_available_models()}. Please pull the model using: ollama pull {model}"
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
        
        response_text = response["message"]["content"]
        
        # Extract JSON from response
        result = extract_json_from_response(response_text)
        
        # Validate and set defaults
        band_score = float(result.get("bandScore", 6.5))
        pronunciation_score = float(result.get("pronunciationScore", 6.0))
        grammar_score = float(result.get("grammarScore", 6.5))
        vocabulary_score = float(result.get("vocabularyScore", 6.0))
        fluency_score = float(result.get("fluencyScore", 6.5))
        overall_feedback = result.get("overallFeedback", "Evaluation completed.")
        
        # Clamp scores to valid range
        def clamp_score(score):
            return max(0.0, min(9.0, float(score)))
        
        return {
            "bandScore": clamp_score(band_score),
            "pronunciationScore": clamp_score(pronunciation_score),
            "grammarScore": clamp_score(grammar_score),
            "vocabularyScore": clamp_score(vocabulary_score),
            "fluencyScore": clamp_score(fluency_score),
            "overallFeedback": overall_feedback
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )


class GenerateRequest(BaseModel):
    """Request model for text generation endpoint"""
    prompt: str
    task_type: Optional[str] = "general"  # topics, questions, outline, vocabulary, structures, refine, compare
    context: Optional[dict] = None
    format: Optional[dict] = None


@app.post("/api/generate")
async def generate(request: GenerateRequest):
    """
    Generic text generation endpoint for various tasks
    
    **Request body:**
    ```json
    {
        "prompt": "Generate IELTS topics...",
        "task_type": "topics",
        "context": {"partNumber": 1, "difficultyLevel": "intermediate"},
        "format": {"topics": []}
    }
    ```
    """
    # Retry connection check before processing
    if not ollama_available:
        check_ollama_connection()
    
    if not ollama_available:
        error_msg = "Ollama service is not available. Please ensure Ollama server is running."
        if ollama_error:
            error_msg += f" Error: {ollama_error}"
        raise HTTPException(
            status_code=503,
            detail=error_msg
        )
    
    try:
        # Build system message based on task type
        system_messages = {
            "topics": "You are an expert IELTS content creator. Generate IELTS speaking topics in JSON format.",
            "questions": "You are an expert IELTS content creator. Generate IELTS speaking questions with sample answers, vocabulary, and structures in JSON format.",
            "outline": "You are an expert IELTS speaking coach. Generate speaking outlines and structures in JSON format.",
            "vocabulary": "You are an expert English teacher. Generate vocabulary lists with definitions, examples, and pronunciation in JSON format.",
            "structures": "You are an expert English teacher. Generate sample sentence structures and patterns in JSON format.",
            "refine": "You are an expert IELTS speaking coach. Refine and improve speaking responses while preserving the original style.",
            "compare": "You are an expert IELTS speaking coach. Compare two versions of text and highlight improvements.",
            "general": "You are a helpful AI assistant. Generate content in the requested format."
        }
        
        system_message = system_messages.get(request.task_type, system_messages["general"])
        
        # Add context to prompt if provided
        user_prompt = request.prompt
        if request.context:
            context_str = ", ".join([f"{k}: {v}" for k, v in request.context.items()])
            user_prompt = f"{user_prompt}\n\nContext: {context_str}"
        
        messages = [
            {"role": "system", "content": f"{system_message} Return valid JSON only."},
            {"role": "user", "content": user_prompt}
        ]
        
        # Call Ollama
        model = OLLAMA_MODEL
        try:
            response = ollama_client.chat(
                model=model,
                messages=messages,
                options={
                    "temperature": 0.7,  # Higher temperature for more creative generation
                    "num_predict": 2000  # Allow longer responses for generation
                }
            )
        except Exception as ollama_error:
            error_str = str(ollama_error).lower()
            if "model" in error_str and ("not found" in error_str or "does not exist" in error_str):
                raise HTTPException(
                    status_code=404,
                    detail=f"Model '{model}' not found. Available models: {_get_available_models()}"
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
        
        response_text = response["message"]["content"]
        
        # Try to extract JSON from response
        try:
            # Try to parse as JSON directly
            result = json.loads(response_text)
        except:
            # Try to extract JSON from markdown code blocks or text
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                except:
                    # Fallback: return text as-is
                    result = {"content": response_text}
            else:
                # Try to find JSON object in text
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(0))
                    except:
                        result = {"content": response_text}
                else:
                    result = {"content": response_text}
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Error processing generation request: {str(e)}"
        )

