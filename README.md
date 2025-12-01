# Llama Service - IELTS Scoring

Service sử dụng Ollama LLM để chấm điểm IELTS speaking.

## Yêu cầu

1. **Ollama Server** phải được cài đặt và chạy
   - Download: https://ollama.ai
   - Chạy: `ollama serve`

2. **Model** phải được download
   ```bash
   ollama pull llama3.1:8b
   # hoặc
   ollama pull llama3.1:70b  # cho độ chính xác cao hơn
   ```

## Cấu hình

### Environment Variables

- `OLLAMA_BASE_URL`: URL của Ollama server (mặc định: `http://localhost:11434`)
- `OLLAMA_MODEL`: Model name để sử dụng (mặc định: `llama3.1:8b`)

### Ví dụ:

```bash
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.1:8b
```

## Cài đặt

```bash
cd services/llama
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
# hoặc
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

## Chạy Service

```bash
uvicorn app.main:app --host 0.0.0.0 --port 11434 --reload
```

## API Endpoints

### POST /api/chat

Chấm điểm IELTS speaking response.

**Request:**
```json
{
  "model": "llama3.1:8b",
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

## Troubleshooting

### Lỗi: Ollama service is not available

**Nguyên nhân:** Ollama server chưa chạy hoặc không kết nối được.

**Cách sửa:**
1. Kiểm tra Ollama đang chạy:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. Khởi động Ollama:
   ```bash
   ollama serve
   ```

3. Kiểm tra model đã download:
   ```bash
   ollama list
   ```

### Lỗi: Model not found

**Cách sửa:**
```bash
ollama pull llama3.1:8b
```












