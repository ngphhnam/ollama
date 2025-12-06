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
# NOTE: Default model is set to "llama3.1:latest"
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
            "chat": "POST /api/chat (advanced chat endpoint)",
            "generate_topics": "POST /api/generate/topics (specialized topics generation)",
            "generate_questions": "POST /api/generate/questions (specialized questions generation)",
            "generate_answers": "POST /api/generate/answers (specialized answers generation)",
            "generate_structures": "POST /api/generate/structures (specialized structures generation)",
            "generate_vocabulary": "POST /api/generate/vocabulary (specialized vocabulary generation)",
            "generate": "POST /api/generate (fallback/playground endpoint)"
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


# ============================================================================
# Shared utility functions for Ollama calls
# ============================================================================

def call_ollama_generate(
    system_message: str,
    user_prompt: str,
    temperature: float = 0.7,
    num_predict: int = 2000,
    model: Optional[str] = None
) -> dict:
    """
    Shared utility function to call Ollama for text generation
    
    Args:
        system_message: System message for the LLM
        user_prompt: User prompt/instruction
        temperature: Temperature for generation (default: 0.7)
        num_predict: Max tokens to predict (default: 2000)
        model: Model name (default: uses OLLAMA_MODEL)
    
    Returns:
        dict: Parsed JSON response from Ollama
    """
    global ollama_client, ollama_available, ollama_error
    
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
    
    messages = [
        {"role": "system", "content": f"{system_message} Return valid JSON only."},
        {"role": "user", "content": user_prompt}
    ]
    
    # Use provided model or default
    model_name = model or OLLAMA_MODEL
    
    try:
        response = ollama_client.chat(
            model=model_name,
            messages=messages,
            options={
                "temperature": temperature,
                "num_predict": num_predict
            }
        )
    except Exception as ollama_error:
        error_str = str(ollama_error).lower()
        if "model" in error_str and ("not found" in error_str or "does not exist" in error_str):
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model_name}' not found. Available models: {_get_available_models()}"
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
        
        # If result is a dict with only "content" key and content is a JSON string, parse it
        if isinstance(result, dict) and len(result) == 1 and "content" in result:
            content_value = result["content"]
            if isinstance(content_value, str):
                try:
                    # Try to parse the content as JSON
                    parsed_content = json.loads(content_value)
                    if isinstance(parsed_content, dict):
                        result = parsed_content
                except:
                    pass  # Keep original result if parsing fails
        
    except:
        # Try to extract JSON from markdown code blocks or text
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
            except:
                # Try to find JSON object in text
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(0))
                    except:
                        result = {"content": response_text}
                else:
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
    
    # Final check: if result is still {"content": "..."} and content looks like JSON, try to parse it
    if isinstance(result, dict) and len(result) == 1 and "content" in result:
        content_value = result["content"]
        if isinstance(content_value, str):
            # Try to extract JSON from the content string
            content_stripped = content_value.strip()
            
            # If it starts with {, try to parse it
            if content_stripped.startswith('{'):
                try:
                    parsed_content = json.loads(content_value)
                    if isinstance(parsed_content, dict):
                        result = parsed_content
                except json.JSONDecodeError as e:
                    # If JSON is malformed, try to extract the JSON object using regex
                    json_match = re.search(r'\{.*\}', content_value, re.DOTALL)
                    if json_match:
                        try:
                            # Try to fix common JSON issues (like newlines in strings)
                            json_str = json_match.group(0)
                            # Try to parse with relaxed rules
                            parsed_content = json.loads(json_str)
                            if isinstance(parsed_content, dict):
                                result = parsed_content
                        except:
                            # If still fails, try to extract just the JSON part more carefully
                            # Look for complete JSON structure
                            brace_count = 0
                            json_start = content_value.find('{')
                            if json_start >= 0:
                                json_end = json_start
                                for i in range(json_start, len(content_value)):
                                    if content_value[i] == '{':
                                        brace_count += 1
                                    elif content_value[i] == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            json_end = i + 1
                                            break
                                if brace_count == 0:
                                    try:
                                        json_str = content_value[json_start:json_end]
                                        parsed_content = json.loads(json_str)
                                        if isinstance(parsed_content, dict):
                                            result = parsed_content
                                    except:
                                        pass  # Keep original result
    
    return result


# ============================================================================
# Request/Response Models for specialized endpoints
# ============================================================================

class TopicsRequest(BaseModel):
    """Request model for topics generation"""
    partNumber: Optional[int] = 1
    difficultyLevel: Optional[str] = "intermediate"
    count: Optional[int] = 5
    topicCategory: Optional[str] = None
    prompt: Optional[str] = None  # Optional custom prompt


class QuestionItem(BaseModel):
    """Model for a single question item"""
    name: str
    questions: List[str]


class TopicsResponse(BaseModel):
    """Response model for topics generation"""
    topics: List[QuestionItem]


class QuestionsRequest(BaseModel):
    """Request model for questions generation"""
    partNumber: Optional[int] = 2
    difficultyLevel: Optional[str] = "intermediate"
    topic: Optional[str] = None
    prompt: Optional[str] = None  # Optional custom prompt


class VocabularyItem(BaseModel):
    """Model for vocabulary item"""
    word: str
    definition: str
    example: str
    pronunciation: Optional[str] = None


class StructureItem(BaseModel):
    """Model for structure item"""
    pattern: str
    example: str
    usage: Optional[str] = None


class QuestionsResponse(BaseModel):
    """Response model for questions generation"""
    question: str
    sampleAnswer: str
    vocabulary: List[VocabularyItem]
    structures: List[StructureItem]


class AnswersRequest(BaseModel):
    """Request model for answers generation"""
    question: str
    partNumber: Optional[int] = 2
    targetBand: Optional[float] = 7.0


class AnswersResponse(BaseModel):
    """Response model for answers generation"""
    answer: str
    vocabulary: List[VocabularyItem]
    structures: List[StructureItem]
    keyPoints: Optional[List[str]] = None


class StructuresRequest(BaseModel):
    """Request model for structures generation"""
    question: str
    partNumber: Optional[int] = 3
    targetBand: Optional[float] = 7.0
    count: Optional[int] = 5


class StructuresResponse(BaseModel):
    """Response model for structures generation"""
    structures: List[StructureItem]


class VocabularyRequest(BaseModel):
    """Request model for vocabulary generation"""
    question: str
    targetBand: Optional[float] = 7.0
    count: Optional[int] = 10


class VocabularyResponse(BaseModel):
    """Response model for vocabulary generation"""
    vocabulary: List[VocabularyItem]


class GenerateRequest(BaseModel):
    """Request model for text generation endpoint (fallback/playground)"""
    prompt: str
    task_type: Optional[str] = "general"  # topics, questions, outline, vocabulary, structures, refine, compare
    context: Optional[dict] = None
    format: Optional[dict] = None


# ============================================================================
# Specialized Generation Endpoints
# ============================================================================

@app.post("/api/generate/topics", response_model=TopicsResponse)
async def generate_topics(request: TopicsRequest):
    """
    Generate IELTS Speaking topics with related questions
    
    **Request body:**
    ```json
    {
        "partNumber": 1,
        "difficultyLevel": "intermediate",
        "count": 5,
        "topicCategory": "daily life"
    }
    ```
    
    **Response:**
    ```json
    {
        "topics": [
            {
                "name": "Hobbies",
                "questions": ["What hobbies do you enjoy?", "How often do you do this?"]
            }
        ]
    }
    ```
    """
    try:
        # Build prompt
        if request.prompt:
            user_prompt = request.prompt
        else:
            user_prompt = f"""Generate {request.count or 5} IELTS Speaking Part {request.partNumber or 1} topics about {request.topicCategory or 'daily life and hobbies'}.
Each topic should have 3-4 related questions.
Difficulty level: {request.difficultyLevel or 'intermediate'}

Return JSON in this exact format:
{{
    "topics": [
        {{
            "name": "Topic name",
            "questions": ["Question 1", "Question 2", "Question 3"]
        }}
    ]
}}"""
        
        system_message = "You are an expert IELTS content creator. Generate IELTS speaking topics in JSON format."
        
        result = call_ollama_generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            num_predict=1500
        )
        
        # Validate and return
        if "topics" not in result:
            raise HTTPException(status_code=500, detail="Invalid response format: missing 'topics' field")
        
        return TopicsResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating topics: {str(e)}"
        )


@app.post("/api/generate/questions", response_model=QuestionsResponse)
async def generate_questions(request: QuestionsRequest):
    """
    Generate IELTS Speaking questions with sample answers, vocabulary, and structures
    
    **Request body:**
    ```json
    {
        "partNumber": 2,
        "difficultyLevel": "intermediate",
        "topic": "Travel"
    }
    ```
    
    **Response:**
    ```json
    {
        "question": "Describe a memorable trip...",
        "sampleAnswer": "I'd like to talk about...",
        "vocabulary": [
            {
                "word": "memorable",
                "definition": "worth remembering",
                "example": "It was a memorable experience",
                "pronunciation": "/ˈmemərəbəl/"
            }
        ],
        "structures": [
            {
                "pattern": "I'd like to talk about...",
                "example": "I'd like to talk about my trip to Japan",
                "usage": "Opening phrase for Part 2"
            }
        ]
    }
    ```
    """
    try:
        # Build prompt
        if request.prompt:
            user_prompt = request.prompt
        else:
            topic_part = f" about '{request.topic}'" if request.topic else ""
            user_prompt = f"""Generate an IELTS Speaking Part {request.partNumber or 2} cue card{topic_part}.
Include:
1. The question/prompt
2. A sample answer (2-3 minutes speaking time)
3. Key vocabulary with definitions, examples, and pronunciation
4. Useful sentence structures with examples

Difficulty level: {request.difficultyLevel or 'intermediate'}

Return JSON in this exact format:
{{
    "question": "The cue card question/prompt",
    "sampleAnswer": "A detailed sample answer (2-3 minutes of speaking)",
    "vocabulary": [
        {{
            "word": "word",
            "definition": "definition",
            "example": "example sentence",
            "pronunciation": "/pronunciation/"
        }}
    ],
    "structures": [
        {{
            "pattern": "sentence pattern",
            "example": "example sentence",
            "usage": "when to use this structure"
        }}
    ]
}}"""
        
        system_message = "You are an expert IELTS content creator. Generate IELTS speaking questions with sample answers, vocabulary, and structures in JSON format."
        
        result = call_ollama_generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            num_predict=2500
        )
        
        # Validate and return
        required_fields = ["question", "sampleAnswer", "vocabulary", "structures"]
        for field in required_fields:
            if field not in result:
                raise HTTPException(status_code=500, detail=f"Invalid response format: missing '{field}' field")
        
        return QuestionsResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating questions: {str(e)}"
        )


@app.post("/api/generate/answers", response_model=AnswersResponse)
async def generate_answers(request: AnswersRequest):
    """
    Generate sample answers for IELTS Speaking questions
    
    **Request body:**
    ```json
    {
        "question": "Describe a memorable trip",
        "partNumber": 2,
        "targetBand": 7.0
    }
    ```
    
    **Response:**
    ```json
    {
        "answer": "I'd like to talk about...",
        "vocabulary": [...],
        "structures": [...],
        "keyPoints": ["Point 1", "Point 2"]
    }
    ```
    """
    try:
        # Build prompt
        user_prompt = f"""Generate a sample answer for this IELTS Speaking Part {request.partNumber or 2} question:

Question: {request.question}

Requirements:
- Target band score: {request.targetBand or 7.0}
- Answer should be suitable for 2-3 minutes of speaking
- Include advanced vocabulary and complex structures appropriate for the target band
- Provide key vocabulary with definitions, examples, and pronunciation
- Provide useful sentence structures with examples
- List key points covered in the answer

IMPORTANT: You MUST return ONLY valid JSON. Do not include any text before or after the JSON. The JSON must have these exact field names:
- "answer" (required - the complete sample answer text)
- "vocabulary" (required - array of vocabulary items)
- "structures" (required - array of structure items)
- "keyPoints" (optional - array of strings)

Return JSON in this exact format (use these exact field names):
{{
    "answer": "The complete sample answer (2-3 minutes of speaking)",
    "vocabulary": [
        {{
            "word": "word",
            "definition": "definition",
            "example": "example sentence",
            "pronunciation": "/pronunciation/"
        }}
    ],
    "structures": [
        {{
            "pattern": "sentence pattern",
            "example": "example sentence",
            "usage": "when to use this structure"
        }}
    ],
    "keyPoints": ["Key point 1", "Key point 2", "Key point 3"]
}}"""
        
        system_message = "You are an expert IELTS speaking coach. Generate high-quality sample answers with vocabulary and structures in JSON format."
        
        result = call_ollama_generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            num_predict=2500
        )
        
        # Handle alternative field names (LLM might use different names)
        if "sampleAnswer" in result and "answer" not in result:
            result["answer"] = result["sampleAnswer"]
        if "sample_answer" in result and "answer" not in result:
            result["answer"] = result["sample_answer"]
        
        # Validate and return
        required_fields = ["answer", "vocabulary", "structures"]
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            # Provide more helpful error message with what was actually returned
            returned_fields = list(result.keys())
            raise HTTPException(
                status_code=500, 
                detail=f"Invalid response format: missing fields {missing_fields}. Returned fields: {returned_fields}. Response preview: {str(result)[:500]}"
            )
        
        return AnswersResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating answers: {str(e)}"
        )


@app.post("/api/generate/structures", response_model=StructuresResponse)
async def generate_structures(request: StructuresRequest):
    """
    Generate useful sentence structures for IELTS Speaking
    
    **Request body:**
    ```json
    {
        "question": "What are the benefits of online learning?",
        "partNumber": 3,
        "targetBand": 7.0,
        "count": 5
    }
    ```
    
    **Response:**
    ```json
    {
        "structures": [
            {
                "pattern": "I believe that...",
                "example": "I believe that education is crucial",
                "usage": "Expressing strong opinions"
            }
        ]
    }
    ```
    """
    try:
        # Build prompt
        user_prompt = f"""Generate {request.count or 5} useful sentence structures for answering this IELTS Speaking Part {request.partNumber or 3} question:

Question: {request.question}

Requirements:
- Target band score: {request.targetBand or 7.0}
- Structures should be appropriate for the target band level
- Each structure should be relevant to answering the question

Each structure should include:
- The pattern/formula
- A clear example sentence related to the question
- When/how to use it

Return JSON in this exact format:
{{
    "structures": [
        {{
            "pattern": "sentence pattern/formula",
            "example": "example sentence using the pattern",
            "usage": "explanation of when and how to use this structure"
        }}
    ]
}}"""
        
        system_message = "You are an expert English teacher. Generate sample sentence structures and patterns in JSON format."
        
        result = call_ollama_generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            num_predict=1500
        )
        
        # Validate and return
        if "structures" not in result:
            raise HTTPException(status_code=500, detail="Invalid response format: missing 'structures' field")
        
        return StructuresResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating structures: {str(e)}"
        )


@app.post("/api/generate/vocabulary", response_model=VocabularyResponse)
async def generate_vocabulary(request: VocabularyRequest):
    """
    Generate vocabulary lists with definitions, examples, and pronunciation
    
    **Request body:**
    ```json
    {
        "question": "Describe a memorable trip you have taken",
        "targetBand": 7.0,
        "count": 10
    }
    ```
    
    **Response:**
    ```json
    {
        "vocabulary": [
            {
                "word": "curriculum",
                "definition": "the subjects comprising a course of study",
                "example": "The school has updated its curriculum",
                "pronunciation": "/kəˈrɪkjələm/"
            }
        ]
    }
    ```
    """
    try:
        # Build prompt
        user_prompt = f"""Generate a vocabulary list of {request.count or 10} words relevant to answering this IELTS Speaking question:

Question: {request.question}

Requirements:
- Target band score: {request.targetBand or 7.0}
- Vocabulary should be appropriate for the target band level
- Words should be relevant and useful for answering the question

For each word, provide:
- Word
- Definition
- Example sentence (preferably related to the question)
- Pronunciation guide (IPA format)

Return JSON in this exact format:
{{
    "vocabulary": [
        {{
            "word": "word",
            "definition": "clear definition",
            "example": "example sentence using the word",
            "pronunciation": "/pronunciation in IPA/"
        }}
    ]
}}"""
        
        system_message = "You are an expert English teacher. Generate vocabulary lists with definitions, examples, and pronunciation in JSON format."
        
        result = call_ollama_generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            num_predict=2000
        )
        
        # Validate and return
        if "vocabulary" not in result:
            raise HTTPException(status_code=500, detail="Invalid response format: missing 'vocabulary' field")
        
        return VocabularyResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating vocabulary: {str(e)}"
        )


# ============================================================================
# Fallback/Playground Endpoint (kept for backward compatibility)
# ============================================================================

@app.post("/api/generate")
async def generate(request: GenerateRequest):
    """
    Generic text generation endpoint for various tasks (FALLBACK/PLAYGROUND)
    
    ⚠️ NOTE: This is a fallback/playground endpoint for experimentation.
    For production use, please use the specialized endpoints:
    - POST /api/generate/topics
    - POST /api/generate/questions
    - POST /api/generate/answers
    - POST /api/generate/structures
    - POST /api/generate/vocabulary
    
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
        
        # Use shared utility function
        result = call_ollama_generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            num_predict=2000
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Error processing generation request: {str(e)}"
        )

