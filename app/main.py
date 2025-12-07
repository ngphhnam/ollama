from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

from app.routers import v1_router, v2_router
from app.services import ollama_service, google_ai_service

app = FastAPI(title="Llama Service", version="2.0.0")

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

# Include routers
app.include_router(v1_router)
app.include_router(v2_router)


@app.get("/")
async def root():
    """Root endpoint with service status"""
    return {
        "status": "ok",
        "service": "llama",
        "version": "2.0.0",
        "ollama_available": ollama_service.available,
        "ollama_url": ollama_service.base_url,
        "default_model": ollama_service.default_model,
        "ollama_error": ollama_service.error if not ollama_service.available else None,
        "google_ai_available": google_ai_service.available,
        "google_ai_error": google_ai_service.error if not google_ai_service.available else None,
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    ollama_healthy = ollama_service.available
    google_ai_healthy = google_ai_service.available
    
    # Service is healthy if at least one provider is available
    overall_status = "healthy" if (ollama_healthy or google_ai_healthy) else "degraded"
    
    return {
        "status": overall_status,
        "service": "llama",
        "version": "2.0.0",
        "ollama_available": ollama_healthy,
        "google_ai_available": google_ai_healthy,
    }


@app.post("/reconnect")
async def reconnect():
    """Manually retry Ollama connection"""
    success = ollama_service.reconnect()
    return {
        "success": success,
        "ollama_available": ollama_service.available,
        "ollama_url": ollama_service.base_url,
        "error": ollama_service.error if not success else None
    }


@app.get("/info")
async def info():
    """Get service information"""
    return {
        "service": "Llama IELTS Scoring Service",
        "version": "2.0.0",
        "description": "IELTS speaking scoring using Ollama LLM and Google AI Studio",
        "ollama_available": ollama_service.available,
        "ollama_url": ollama_service.base_url,
        "default_model": ollama_service.default_model,
        "google_ai_available": google_ai_service.available,
        "endpoints": {
            "health": "GET /health",
            "info": "GET /info",
            "reconnect": "POST /reconnect",
            # v1 endpoints (Ollama)
            "v1_score": "POST /api/score (v1 - Ollama)",
            "v1_chat": "POST /api/chat (v1 - Ollama)",
            "v1_generate_topics": "POST /api/generate/topics (v1 - Ollama)",
            "v1_generate_questions": "POST /api/generate/questions (v1 - Ollama)",
            "v1_generate_answers": "POST /api/generate/answers (v1 - Ollama)",
            "v1_generate_structures": "POST /api/generate/structures (v1 - Ollama)",
            "v1_generate_vocabulary": "POST /api/generate/vocabulary (v1 - Ollama)",
            "v1_generate": "POST /api/generate (v1 - Ollama, fallback/playground)",
            "v1_grammar_correct": "POST /api/grammar/correct (v1 - Ollama)",
            "v1_improve": "POST /api/improve (v1 - Ollama)",
            "v2_score": "POST /api/v2/score ",
            "v2_chat": "POST /api/v2/chat",
            "v2_generate_topics": "POST /api/v2/generate/topics ",
            "v2_generate_questions": "POST /api/v2/generate/questions ",
            "v2_generate_answers": "POST /api/v2/generate/answers ",
            "v2_generate_structures": "POST /api/v2/generate/structures ",
            "v2_generate_vocabulary": "POST /api/v2/generate/vocabulary ",
            "v2_generate": "POST /api/v2/generate ",
            "v2_grammar_correct": "POST /api/v2/grammar/correct ",
            "v2_improve": "POST /api/v2/improve ",
            "v2_list_models": "GET /api/v2/models ",
        }
    }
