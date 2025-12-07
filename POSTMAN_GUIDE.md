# Hướng dẫn sử dụng API Generate với Postman

## Tổng quan

API `/api/generate` là endpoint để tạo nội dung IELTS tự động sử dụng Ollama LLM. API này hỗ trợ nhiều loại task khác nhau như tạo topics, questions, vocabulary, structures, v.v.

## Thông tin cơ bản

- **Base URL**: `http://localhost:8000` (hoặc port mà bạn đã cấu hình)
- **Endpoint**: `POST /api/generate`
- **Content-Type**: `application/json`

## Cấu trúc Request

```json
{
  "prompt": "string (bắt buộc)",
  "task_type": "string (tùy chọn, mặc định: 'general')",
  "context": {
    "key": "value"
  },
  "format": {
    "key": "value"
  }
}
```

### Các tham số

- **prompt** (bắt buộc): Câu lệnh/prompt để AI tạo nội dung
- **task_type** (tùy chọn): Loại task, các giá trị có thể:
  - `topics`: Tạo IELTS topics
  - `questions`: Tạo IELTS questions với đáp án
  - `outline`: Tạo speaking outlines
  - `vocabulary`: Tạo vocabulary lists
  - `structures`: Tạo sentence structures
  - `refine`: Cải thiện speaking response
  - `compare`: So sánh hai phiên bản text
  - `general`: Tạo nội dung chung (mặc định)
- **context** (tùy chọn): Thông tin bổ sung như partNumber, difficultyLevel, etc.
- **format** (tùy chọn): Định dạng output mong muốn

## Ví dụ Request cho Postman

### 1. Tạo IELTS Topics (Part 1)

**Method**: `POST`  
**URL**: `http://localhost:8000/api/generate`  
**Headers**:
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "prompt": "Generate 5 IELTS Speaking Part 1 topics about daily life and hobbies. Each topic should have 3-4 related questions.",
  "task_type": "topics",
  "context": {
    "partNumber": 1,
    "difficultyLevel": "intermediate"
  },
  "format": {
    "topics": [
      {
        "name": "string",
        "questions": ["string"]
      }
    ]
  }
}
```

**Response mẫu**:
```json
{
  "topics": [
    {
      "name": "Daily Routine",
      "questions": [
        "What time do you usually wake up?",
        "Do you have a regular daily schedule?",
        "What do you do in your free time?"
      ]
    },
    {
      "name": "Hobbies",
      "questions": [
        "Do you have any hobbies?",
        "How long have you been interested in this hobby?",
        "Why do you enjoy this hobby?"
      ]
    }
  ]
}
```

---

### 2. Tạo IELTS Questions với Sample Answers (Part 2)

**Method**: `POST`  
**URL**: `http://localhost:8000/api/generate`  
**Headers**:
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "prompt": "Generate an IELTS Speaking Part 2 cue card about 'Describe a memorable trip'. Include the question, sample answer, key vocabulary, and useful structures.",
  "task_type": "questions",
  "context": {
    "partNumber": 2,
    "difficultyLevel": "intermediate",
    "topic": "Travel"
  },
  "format": {
    "question": "string",
    "sampleAnswer": "string",
    "vocabulary": ["string"],
    "structures": ["string"]
  }
}
```

**Response mẫu**:
```json
{
  "question": "Describe a memorable trip you have taken. You should say: where you went, who you went with, what you did, and explain why it was memorable.",
  "sampleAnswer": "I'd like to talk about a trip I took to Japan last summer...",
  "vocabulary": [
    "memorable - đáng nhớ",
    "breathtaking - ngoạn mục",
    "immersive - đắm chìm"
  ],
  "structures": [
    "I'd like to talk about...",
    "What made it special was...",
    "Looking back, I realize..."
  ]
}
```

---

### 3. Tạo Vocabulary List

**Method**: `POST`  
**URL**: `http://localhost:8000/api/generate`  
**Headers**:
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "prompt": "Generate a vocabulary list of 10 advanced words related to 'Education' with definitions, examples, and pronunciation guide.",
  "task_type": "vocabulary",
  "context": {
    "topic": "Education",
    "level": "advanced",
    "count": 10
  },
  "format": {
    "vocabulary": [
      {
        "word": "string",
        "definition": "string",
        "example": "string",
        "pronunciation": "string"
      }
    ]
  }
}
```

**Response mẫu**:
```json
{
  "vocabulary": [
    {
      "word": "curriculum",
      "definition": "the subjects comprising a course of study",
      "example": "The school has updated its curriculum to include more technology courses.",
      "pronunciation": "/kəˈrɪkjələm/"
    },
    {
      "word": "pedagogy",
      "definition": "the method and practice of teaching",
      "example": "Modern pedagogy emphasizes student-centered learning.",
      "pronunciation": "/ˈpedəɡɒdʒi/"
    }
  ]
}
```

---

### 4. Tạo Sentence Structures

**Method**: `POST`  
**URL**: `http://localhost:8000/api/generate`  
**Headers**:
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "prompt": "Generate 5 useful sentence structures for expressing opinions in IELTS Speaking Part 3, with examples.",
  "task_type": "structures",
  "context": {
    "partNumber": 3,
    "function": "expressing opinions"
  },
  "format": {
    "structures": [
      {
        "pattern": "string",
        "example": "string",
        "usage": "string"
      }
    ]
  }
}
```

**Response mẫu**:
```json
{
  "structures": [
    {
      "pattern": "From my perspective, ...",
      "example": "From my perspective, technology has both advantages and disadvantages.",
      "usage": "Use to introduce personal viewpoint"
    },
    {
      "pattern": "I tend to think that...",
      "example": "I tend to think that online learning is more flexible.",
      "usage": "Use to express a tendency or inclination"
    }
  ]
}
```

---

### 5. Cải thiện Speaking Response (Refine)

**Method**: `POST`  
**URL**: `http://localhost:8000/api/generate`  
**Headers**:
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "prompt": "Refine and improve this IELTS speaking response while keeping the original meaning and style. Make it more natural and add advanced vocabulary:\n\n'I like travel. I go many places. It is fun. I see new things.'",
  "task_type": "refine",
  "context": {
    "targetBand": 7,
    "preserveStyle": true
  }
}
```

**Response mẫu**:
```json
{
  "original": "I like travel. I go many places. It is fun. I see new things.",
  "refined": "I'm passionate about traveling and have been fortunate enough to visit numerous destinations. What I find most enjoyable is the opportunity to immerse myself in different cultures and discover new perspectives. Each journey offers unique experiences that broaden my horizons.",
  "improvements": [
    "Added advanced vocabulary: passionate, fortunate, immerse, perspectives, broaden horizons",
    "Improved grammar: correct verb forms and sentence structure",
    "Enhanced coherence with linking phrases"
  ]
}
```

---

### 6. So sánh hai phiên bản (Compare)

**Method**: `POST`  
**URL**: `http://localhost:8000/api/generate`  
**Headers**:
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "prompt": "Compare these two IELTS speaking responses and highlight improvements:\n\nVersion 1: 'I like music. It is good. I listen every day.'\n\nVersion 2: 'I'm really passionate about music, and I listen to it on a daily basis. What I find most appealing is how it can evoke different emotions and help me relax after a long day.'",
  "task_type": "compare",
  "context": {
    "focus": "vocabulary and grammar improvements"
  }
}
```

**Response mẫu**:
```json
{
  "comparison": {
    "version1": {
      "text": "I like music. It is good. I listen every day.",
      "bandScore": "4.5-5.0",
      "issues": ["Simple vocabulary", "Basic grammar", "Lacks detail"]
    },
    "version2": {
      "text": "I'm really passionate about music, and I listen to it on a daily basis. What I find most appealing is how it can evoke different emotions and help me relax after a long day.",
      "bandScore": "7.0-7.5",
      "strengths": ["Advanced vocabulary (passionate, appealing, evoke)", "Complex grammar structures", "Detailed explanation"]
    },
    "keyImprovements": [
      "Vocabulary: 'like' → 'passionate about'",
      "Grammar: Added complex sentence structures",
      "Content: Added reasons and personal connection"
    ]
  }
}
```

---

### 7. Tạo Speaking Outline

**Method**: `POST`  
**URL**: `http://localhost:8000/api/generate`  
**Headers**:
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "prompt": "Create a speaking outline for IELTS Part 2 topic 'Describe a person who influenced you'. Include structure, key points, and useful phrases.",
  "task_type": "outline",
  "context": {
    "partNumber": 2,
    "topic": "Person"
  },
  "format": {
    "structure": {
      "introduction": "string",
      "mainPoints": ["string"],
      "conclusion": "string"
    },
    "usefulPhrases": ["string"]
  }
}
```

**Response mẫu**:
```json
{
  "structure": {
    "introduction": "Introduce the person and your relationship",
    "mainPoints": [
      "Describe their appearance and personality",
      "Explain how they influenced you",
      "Give specific examples of their impact"
    ],
    "conclusion": "Summarize their importance in your life"
  },
  "usefulPhrases": [
    "I'd like to talk about...",
    "What stands out about them is...",
    "They've had a profound impact on...",
    "Looking back, I realize..."
  ]
}
```

---

### 8. Tạo nội dung chung (General)

**Method**: `POST`  
**URL**: `http://localhost:8000/api/generate`  
**Headers**:
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "prompt": "Write a short paragraph explaining the benefits of learning English for career development.",
  "task_type": "general"
}
```

**Response mẫu**:
```json
{
  "content": "Learning English offers numerous advantages for career development. In today's globalized world, English serves as the lingua franca of international business, enabling professionals to communicate effectively with colleagues, clients, and partners worldwide. Proficiency in English opens doors to better job opportunities, higher salaries, and career advancement. Many multinational companies require English fluency, and it's often a prerequisite for leadership positions. Additionally, English provides access to a vast repository of knowledge, research, and professional resources that can enhance one's expertise and competitiveness in the job market."
}
```

---

## Cấu hình Postman Collection

### Tạo Collection trong Postman

1. Tạo Collection mới tên "IELTS Generate API"
2. Thêm các request như trên
3. Thiết lập Environment Variables:
   - `base_url`: `http://localhost:8000`
   - `ollama_url`: `http://localhost:11434`

### Sử dụng Environment Variables

Trong Postman, bạn có thể tạo Environment với các biến:
- `{{base_url}}` = `http://localhost:8000`

Sau đó URL sẽ là: `{{base_url}}/api/generate`

---

## Kiểm tra Service

Trước khi test API, đảm bảo:

1. **Ollama Server đang chạy**:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **Service đang chạy**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **Kiểm tra thông tin service**:
   ```bash
   curl http://localhost:8000/info
   ```

---

## Xử lý lỗi

### Lỗi 503: Ollama service is not available

**Nguyên nhân**: Ollama server chưa chạy hoặc không kết nối được.

**Giải pháp**:
1. Kiểm tra Ollama đang chạy: `ollama serve`
2. Kiểm tra URL trong environment variable `OLLAMA_BASE_URL`
3. Gọi endpoint `/reconnect` để thử kết nối lại:
   ```json
   POST http://localhost:8000/reconnect
   ```

### Lỗi 404: Model not found

**Nguyên nhân**: Model chưa được download.

**Giải pháp**:
```bash
ollama pull llama3.1:latest
```

### Lỗi 500: Error processing generation request

**Nguyên nhân**: Lỗi trong quá trình xử lý.

**Giải pháp**: Kiểm tra log của service để xem chi tiết lỗi.

---

## Tips khi sử dụng

1. **Prompt rõ ràng**: Viết prompt cụ thể và chi tiết để có kết quả tốt hơn
2. **Sử dụng context**: Thêm thông tin context để AI hiểu rõ yêu cầu
3. **Định dạng output**: Sử dụng `format` để chỉ định cấu trúc JSON mong muốn
4. **Task type phù hợp**: Chọn đúng `task_type` để có system message phù hợp
5. **Test từng bước**: Bắt đầu với request đơn giản trước khi thử các request phức tạp

---

## Export Postman Collection

Bạn có thể export collection này để chia sẻ với team. File JSON sẽ có dạng:

```json
{
  "info": {
    "name": "IELTS Generate API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Generate Topics",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"prompt\": \"...\",\n  \"task_type\": \"topics\"\n}"
        },
        "url": {
          "raw": "{{base_url}}/api/generate",
          "host": ["{{base_url}}"],
          "path": ["api", "generate"]
        }
      }
    }
  ]
}
```


