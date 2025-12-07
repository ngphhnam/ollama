# Cấu trúc dự án

## Tổng quan
Dự án đã được tách thành các module riêng biệt để dễ quản lý và bảo trì.

## Cấu trúc thư mục

```
app/
├── main.py                 # Entry point, FastAPI app, basic endpoints
├── models/                 # Pydantic models/schemas
│   ├── __init__.py
│   └── schemas.py          # Tất cả request/response models
├── services/               # LLM service layers
│   ├── __init__.py
│   ├── ollama_service.py   # Service cho Ollama
│   └── google_ai_service.py # Service cho Google AI Studio
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── prompts.py          # Prompt building functions
│   └── json_extractor.py   # JSON extraction from LLM responses
└── routers/                # API route handlers
    ├── __init__.py
    ├── v1.py               # API v1 routes (Ollama)
    └── v2.py               # API v2 routes (Google AI Studio)
```

## API Endpoints

### V1 (Ollama) - `/api/*`
- `POST /api/score` - Score IELTS speaking response
- `POST /api/chat` - Chat endpoint
- `POST /api/generate/topics` - Generate topics
- `POST /api/generate/questions` - Generate questions
- `POST /api/generate/answers` - Generate answers
- `POST /api/generate/structures` - Generate structures
- `POST /api/generate/vocabulary` - Generate vocabulary
- `POST /api/generate` - Fallback/playground endpoint

### V2 (Google AI Studio) - `/api/v2/*`
- `POST /api/v2/score` - Score IELTS speaking response
- `POST /api/v2/chat` - Chat endpoint
- `POST /api/v2/generate/topics` - Generate topics
- `POST /api/v2/generate/questions` - Generate questions
- `POST /api/v2/generate/answers` - Generate answers
- `POST /api/v2/generate/structures` - Generate structures
- `POST /api/v2/generate/vocabulary` - Generate vocabulary
- `POST /api/v2/generate` - Fallback/playground endpoint

## Environment Variables

### Ollama (V1)
- `OLLAMA_BASE_URL` - Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL` - Default model name (default: llama3.1:latest)

### Google AI Studio (V2)
- `GOOGLE_AI_API_KEY` - Google AI API key (required for v2)
- `GOOGLE_AI_MODEL` - Model name (default: gemini-pro)

## Chạy ứng dụng

```bash
# Từ thư mục gốc dự án
uvicorn app.main:app --reload
```

## Lưu ý

- V1 endpoints yêu cầu Ollama server đang chạy
- V2 endpoints yêu cầu `GOOGLE_AI_API_KEY` được set trong environment variables
- Cả hai version có cùng request/response format, chỉ khác backend LLM

