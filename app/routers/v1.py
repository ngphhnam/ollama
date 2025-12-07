"""API v1 routes using Ollama"""
from fastapi import APIRouter, HTTPException
from app.models import (
    ScoreRequest,
    ChatPayload,
    TopicsRequest,
    TopicsResponse,
    QuestionsRequest,
    QuestionsResponse,
    AnswersRequest,
    AnswersResponse,
    StructuresRequest,
    StructuresResponse,
    VocabularyRequest,
    VocabularyResponse,
    GenerateRequest,
    GrammarCorrectionRequest,
    GrammarCorrectionResponse,
    ImproveRequest,
    ImproveResponse,
)
from app.services import ollama_service
from app.utils import build_ielts_prompt, extract_json_from_response
from app.utils.json_extractor import extract_json_from_generate_response

router = APIRouter(prefix="/api", tags=["v1"])


@router.post("/score")
async def score(request: ScoreRequest):
    """
    Score IELTS speaking response directly (v1 - Ollama)
    
    Simplified endpoint that takes transcription, topic, and level directly.
    """
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
        response_text = ollama_service.chat(
            messages=messages,
            temperature=0.3,
            num_predict=500
        )
        
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
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing scoring request: {str(e)}"
        )


@router.post("/chat")
async def chat(payload: ChatPayload):
    """
    Score IELTS speaking response using Ollama LLM (v1)
    """
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
            prompt = build_ielts_prompt(transcription, "", topic, level)
            messages = [
                {"role": "system", "content": "You are an expert IELTS speaking examiner. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ]
        else:
            # Use provided messages
            messages = [{"role": msg.role, "content": msg.content} for msg in payload.messages]
        
        # Call Ollama
        model = payload.model or None
        response_text = ollama_service.chat(
            messages=messages,
            model=model,
            temperature=0.3,
            num_predict=500
        )
        
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
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )


@router.post("/generate/topics", response_model=TopicsResponse)
async def generate_topics(request: TopicsRequest):
    """Generate IELTS Speaking topics with related questions (v1 - Ollama)"""
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
        
        response_text = ollama_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            num_predict=1500
        )
        
        result = extract_json_from_generate_response(response_text)
        
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


@router.post("/generate/questions", response_model=QuestionsResponse)
async def generate_questions(request: QuestionsRequest):
    """Generate IELTS Speaking questions with sample answers, vocabulary, and structures (v1 - Ollama)"""
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
        
        response_text = ollama_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            num_predict=2500
        )
        
        result = extract_json_from_generate_response(response_text)
        
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


@router.post("/generate/answers", response_model=AnswersResponse)
async def generate_answers(request: AnswersRequest):
    """Generate sample answers for IELTS Speaking questions (v1 - Ollama)"""
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
        
        response_text = ollama_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            num_predict=2500
        )
        
        result = extract_json_from_generate_response(response_text)
        
        # Handle alternative field names (LLM might use different names)
        if "sampleAnswer" in result and "answer" not in result:
            result["answer"] = result["sampleAnswer"]
        if "sample_answer" in result and "answer" not in result:
            result["answer"] = result["sample_answer"]
        
        # Validate and return
        required_fields = ["answer", "vocabulary", "structures"]
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
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


@router.post("/generate/structures", response_model=StructuresResponse)
async def generate_structures(request: StructuresRequest):
    """Generate useful sentence structures for IELTS Speaking (v1 - Ollama)"""
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
        
        response_text = ollama_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            num_predict=1500
        )
        
        result = extract_json_from_generate_response(response_text)
        
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


@router.post("/generate/vocabulary", response_model=VocabularyResponse)
async def generate_vocabulary(request: VocabularyRequest):
    """Generate vocabulary lists with definitions, examples, and pronunciation (v1 - Ollama)"""
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
        
        response_text = ollama_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            num_predict=2000
        )
        
        result = extract_json_from_generate_response(response_text)
        
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


@router.post("/generate")
async def generate(request: GenerateRequest):
    """
    Generic text generation endpoint for various tasks (FALLBACK/PLAYGROUND) (v1 - Ollama)
    
    ⚠️ NOTE: This is a fallback/playground endpoint for experimentation.
    For production use, please use the specialized endpoints.
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
        
        response_text = ollama_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            num_predict=2000
        )
        
        result = extract_json_from_generate_response(response_text)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing generation request: {str(e)}"
        )


@router.post("/grammar/correct", response_model=GrammarCorrectionResponse)
async def correct_grammar(request: GrammarCorrectionRequest):
    """
    Correct grammar for a transcription (v1 - Ollama)
    
    **Request body:**
    ```json
    {
        "transcription": "I go to school yesterday",
        "textQuestion": "What did you do yesterday?",
        "language": "en"
    }
    ```
    
    **Response:**
    ```json
    {
        "original": "I go to school yesterday",
        "corrected": "I went to school yesterday",
        "corrections": [
            {
                "original": "go",
                "corrected": "went",
                "reason": "Past tense required"
            }
        ],
        "explanation": "Changed 'go' to 'went' because the sentence refers to a past action."
    }
    ```
    """
    try:
        # Build prompt
        question_context = ""
        if request.textQuestion:
            question_context = f"\n\nContext/Question: {request.textQuestion}"
        
        user_prompt = f"""Correct the grammar and improve the following sentence in {request.language or 'English'}:

Sentence to correct: {request.transcription}{question_context}

Requirements:
1. Fix all grammatical errors
2. Improve sentence structure if needed
3. Maintain the original meaning
4. Keep the same style and tone
5. If the sentence is already correct, return it as is

Return JSON in this exact format:
{{
    "original": "the original sentence",
    "corrected": "the corrected sentence",
    "corrections": [
        {{
            "original": "incorrect word/phrase",
            "corrected": "correct word/phrase",
            "reason": "brief explanation of the correction"
        }}
    ],
    "explanation": "Brief explanation of the main corrections made"
}}

IMPORTANT: 
- Return ONLY valid JSON, no additional text
- If no corrections are needed, return the original sentence as corrected
- The corrections array should list all significant corrections made"""
        
        system_message = "You are an expert English grammar teacher. Correct grammar errors and improve sentences while maintaining the original meaning. Return ONLY valid JSON format."
        
        response_text = ollama_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.3,
            num_predict=1500
        )
        
        result = extract_json_from_generate_response(response_text)
        
        # Validate required fields
        required_fields = ["original", "corrected"]
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            returned_fields = list(result.keys())
            raise HTTPException(
                status_code=500,
                detail=f"Invalid response format: missing fields {missing_fields}. Returned fields: {returned_fields}"
            )
        
        # Ensure original and corrected are set
        if "original" not in result:
            result["original"] = request.transcription
        if "corrected" not in result:
            result["corrected"] = request.transcription
        
        return GrammarCorrectionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error correcting grammar: {str(e)}"
        )


@router.post("/improve", response_model=ImproveResponse)
async def improve_sentence(request: ImproveRequest):
    """
    Improve a sentence for IELTS Speaking (v1 - Ollama)
    
    This endpoint improves the sentence by:
    - Fixing grammar errors
    - Using more advanced vocabulary
    - Improving sentence structure
    - Making it more natural and fluent
    
    **Request body:**
    ```json
    {
        "transcription": "I go to school yesterday and I see my friend",
        "questionText": "What did you do yesterday?",
        "language": "en"
    }
    ```
    
    **Response:**
    ```json
    {
        "original": "I go to school yesterday and I see my friend",
        "improved": "I went to school yesterday and saw my friend",
        "improvements": [...],
        "explanation": "...",
        "vocabularySuggestions": [...],
        "structureSuggestions": [...]
    }
    ```
    """
    try:
        # Build prompt
        question_context = ""
        if request.questionText:
            question_context = f"\n\nQuestion/Context: {request.questionText}"
        
        user_prompt = f"""Improve the following FULL transcription for IELTS Speaking in {request.language or 'English'}:

FULL ORIGINAL TRANSCRIPTION (you must improve ALL of it):
{request.transcription}{question_context}

CRITICAL REQUIREMENTS:
1. You MUST improve the ENTIRE transcription, not just a part of it
2. Fix ALL grammatical errors throughout the entire text
3. Correct ALL mispronounced words and transcription errors (e.g., "pretty table" -> "predictable", "off-new up tee" -> "often I have tea")
4. Use more advanced and appropriate vocabulary where suitable
5. Improve sentence structure and make it more natural
6. Maintain the original meaning and context
7. Make it sound more fluent and native-like
8. Keep the same length and structure - improve the ENTIRE text

IMPORTANT: The transcription may contain many errors and mispronunciations. You must process and improve EVERY part of it, not just a small portion.

Return JSON in this exact format:
{{
    "original": "the FULL original transcription",
    "improved": "the FULL improved transcription",
    "improvements": [
        {{
            "type": "grammar|vocabulary|structure|fluency|transcription",
            "original": "original word/phrase",
            "improved": "improved word/phrase",
            "reason": "brief explanation"
        }}
    ],
    "explanation": "Brief explanation of the main improvements made",
    "vocabularySuggestions": [
        {{
            "word": "advanced word",
            "definition": "definition",
            "example": "example sentence",
            "pronunciation": "/pronunciation/"
        }}
    ],
    "structureSuggestions": [
        {{
            "pattern": "sentence pattern",
            "example": "example using the pattern",
            "usage": "when to use"
        }}
    ]
}}

IMPORTANT: 
- Return ONLY valid JSON, no additional text
- The "original" field MUST contain the FULL original transcription
- The "improved" field MUST contain the FULL improved transcription
- Include vocabulary and structure suggestions that would help improve the sentence
- The improvements array should list all significant changes made"""
        
        system_message = "You are an expert IELTS speaking coach. Improve FULL transcriptions by fixing grammar, correcting mispronunciations, using advanced vocabulary, and improving structure. You MUST process the ENTIRE transcription, not just parts of it. Return ONLY valid JSON format."
        
        # Estimate tokens needed for long transcriptions
        input_length = len(request.transcription)
        estimated_tokens = max(2500, int(input_length * 1.5) + 1000)
        
        response_text = ollama_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.3,
            num_predict=min(estimated_tokens, 8000)  # Cap at reasonable limit
        )
        
        result = extract_json_from_generate_response(response_text)
        
        # Validate required fields
        required_fields = ["original", "improved"]
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            returned_fields = list(result.keys())
            raise HTTPException(
                status_code=500,
                detail=f"Invalid response format: missing fields {missing_fields}. Returned fields: {returned_fields}"
            )
        
        # Ensure original and improved are set
        if "original" not in result:
            result["original"] = request.transcription
        if "improved" not in result:
            result["improved"] = request.transcription
        
        # Validate that improved text is reasonable length (at least 50% of original)
        # This helps catch cases where only a small portion was processed
        original_length = len(result.get("original", ""))
        improved_length = len(result.get("improved", ""))
        
        if original_length > 100 and improved_length < original_length * 0.5:
            # Improved text is too short - likely only processed a portion
            raise HTTPException(
                status_code=500,
                detail=f"Response appears incomplete. Original length: {original_length} chars, Improved length: {improved_length} chars. The improved text should be similar length to the original."
            )
        
        return ImproveResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error improving sentence: {str(e)}"
        )

