# Postman Test Data Guide

This guide provides test data examples for all endpoints in the IELTS Llama Service API.

## Base URL
```
http://localhost:8000
```

## Quick Start

1. Import the `IELTS_Generate_API.postman_collection.json` into Postman
2. Set the `base_url` variable to `http://localhost:8000`
3. Use the test data from `postman_test_data.json` in your requests

---

## 1. Scoring Endpoints

### POST /api/score

**Basic Scoring (Intermediate Level)**
```json
{
  "transcription": "I really enjoy traveling because it allows me to experience different cultures and meet new people. Last year, I visited Japan and it was an amazing experience.",
  "topic": "Travel",
  "level": "intermediate"
}
```

**Scoring with Question (Relevance Check)**
```json
{
  "transcription": "I like music very much. I listen to pop songs every day. Music makes me happy and relaxed.",
  "questionText": "What kind of music do you like?",
  "topic": "Music",
  "level": "beginner"
}
```

**Advanced Level Scoring**
```json
{
  "transcription": "I'm particularly fond of classical music, especially compositions from the Romantic period. I find that listening to works by composers like Chopin and Debussy helps me concentrate when I'm studying.",
  "questionText": "What type of music do you enjoy listening to?",
  "topic": "Music",
  "level": "advanced"
}
```

**Off-Topic Test (Should be Penalized)**
```json
{
  "transcription": "I love playing football and watching sports on TV. My favorite team is Manchester United.",
  "questionText": "What kind of music do you like?",
  "topic": "Music",
  "level": "intermediate"
}
```

---

## 2. Specialized Generation Endpoints

### POST /api/generate/topics

**Part 1 Topics - Basic**
```json
{
  "partNumber": 1,
  "difficultyLevel": "intermediate",
  "count": 5,
  "topicCategory": "daily life and hobbies"
}
```

**Part 1 Topics - Advanced**
```json
{
  "partNumber": 1,
  "difficultyLevel": "advanced",
  "count": 8,
  "topicCategory": "technology and innovation"
}
```

**Part 1 Topics - Beginner**
```json
{
  "partNumber": 1,
  "difficultyLevel": "beginner",
  "count": 3,
  "topicCategory": "family and friends"
}
```

### POST /api/generate/questions

**Part 2 Question - Travel**
```json
{
  "partNumber": 2,
  "difficultyLevel": "intermediate",
  "topic": "Travel"
}
```

**Part 2 Question - Education**
```json
{
  "partNumber": 2,
  "difficultyLevel": "advanced",
  "topic": "Education"
}
```

**Part 2 Question - Person**
```json
{
  "partNumber": 2,
  "difficultyLevel": "intermediate",
  "topic": "Person"
}
```

### POST /api/generate/answers

**Answer for Travel Question (Band 7.0)**
```json
{
  "question": "Describe a memorable trip you have taken",
  "partNumber": 2,
  "targetBand": 7.0
}
```

**Answer for Education Question (Band 8.0)**
```json
{
  "question": "Describe a teacher who influenced you",
  "partNumber": 2,
  "targetBand": 8.0
}
```

**Answer for Hobby Question (Band 6.0)**
```json
{
  "question": "Describe your favorite hobby",
  "partNumber": 2,
  "targetBand": 6.0
}
```

### POST /api/generate/structures

**Structures for Part 3 Question**
```json
{
  "question": "What are the benefits of online learning?",
  "partNumber": 3,
  "targetBand": 7.0,
  "count": 5
}
```

**Advanced Structures for Part 3**
```json
{
  "question": "How has technology changed the way we communicate?",
  "partNumber": 3,
  "targetBand": 8.5,
  "count": 8
}
```

### POST /api/generate/vocabulary

**Vocabulary for Travel Topic**
```json
{
  "question": "Describe a memorable trip you have taken",
  "targetBand": 7.0,
  "count": 10
}
```

**Vocabulary for Education Topic (Band 8)**
```json
{
  "question": "What are the advantages of studying abroad?",
  "targetBand": 8.0,
  "count": 15
}
```

---

## 3. Google AI (v2) Endpoints

These endpoints use Google AI Studio for faster responses. Same request format as v1 endpoints.

### POST /api/v2/generate/topics
```json
{
  "partNumber": 1,
  "difficultyLevel": "intermediate",
  "count": 5,
  "topicCategory": "work and career"
}
```

### POST /api/v2/generate/questions
```json
{
  "partNumber": 2,
  "difficultyLevel": "intermediate",
  "topic": "Environment"
}
```

### POST /api/v2/generate/answers
```json
{
  "question": "Describe a place you would like to visit",
  "partNumber": 2,
  "targetBand": 7.5
}
```

### POST /api/v2/generate/structures
```json
{
  "question": "What are the environmental challenges facing the world today?",
  "partNumber": 3,
  "targetBand": 7.0,
  "count": 6
}
```

### POST /api/v2/generate/vocabulary
```json
{
  "question": "Describe a time when you helped someone",
  "targetBand": 7.0,
  "count": 12
}
```

---

## 4. Fallback/Playground Endpoint

### POST /api/generate

**Generate Topics**
```json
{
  "prompt": "Generate 5 IELTS Speaking Part 1 topics about daily life and hobbies. Each topic should have 3-4 related questions.",
  "task_type": "topics",
  "context": {
    "partNumber": 1,
    "difficultyLevel": "intermediate"
  }
}
```

**Refine Response**
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

---

## 5. System Endpoints

### GET /health
No body required. Returns service health status.

### GET /info
No body required. Returns service information and available endpoints.

### GET /
No body required. Returns root status.

### POST /reconnect
No body required. Attempts to reconnect to Ollama server.

---

## Test Scenarios

### Scenario 1: Complete Flow
1. Generate Part 1 topics → `POST /api/generate/topics`
2. Generate Part 2 question → `POST /api/generate/questions`
3. Generate sample answer → `POST /api/generate/answers`
4. Score the answer → `POST /api/score`

### Scenario 2: Vocabulary Learning
1. Generate Part 2 question → `POST /api/generate/questions`
2. Get vocabulary list → `POST /api/generate/vocabulary`
3. Get sentence structures → `POST /api/generate/structures`

### Scenario 3: Different Difficulty Levels
Test the same topic at different levels:
- Beginner: `"difficultyLevel": "beginner"`
- Intermediate: `"difficultyLevel": "intermediate"`
- Advanced: `"difficultyLevel": "advanced"`

---

## Common Topics
- Travel
- Education
- Work
- Hobbies
- Family
- Food
- Music
- Sports
- Technology
- Environment
- Health
- Culture
- Shopping
- Transportation
- Entertainment

## Difficulty Levels
- `beginner`
- `intermediate`
- `advanced`

## Target Bands
- 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0

## Part Numbers
- `1` - Part 1 (Introduction & Interview)
- `2` - Part 2 (Long Turn)
- `3` - Part 3 (Discussion)

---

## Tips for Testing

1. **Start with system endpoints** to verify the service is running
2. **Test scoring first** with simple transcriptions
3. **Use v2 endpoints** (Google AI) for faster responses during development
4. **Test off-topic responses** to verify relevance checking works
5. **Try different difficulty levels** to see how responses vary
6. **Test with and without questionText** in scoring endpoint

---

## Expected Response Formats

### Scoring Response
```json
{
  "bandScore": 7.5,
  "pronunciationScore": 7.0,
  "grammarScore": 7.5,
  "vocabularyScore": 8.0,
  "fluencyScore": 7.0,
  "overallFeedback": "Detailed feedback text..."
}
```

### Topics Response
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

### Questions Response
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

---

## Troubleshooting

- **503 Service Unavailable**: Check if Ollama server is running
- **404 Model Not Found**: Pull the required model: `ollama pull llama3.1:latest`
- **Invalid JSON Response**: The API tries to extract JSON from responses automatically
- **Slow Responses**: Use v2 endpoints (Google AI) for faster generation



