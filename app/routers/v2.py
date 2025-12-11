"""API v2 routes using Google AI Studio"""
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
from app.services import google_ai_service
from app.utils import build_ielts_prompt, extract_json_from_response
from app.utils.json_extractor import extract_json_from_generate_response

router = APIRouter(prefix="/api/v2", tags=["v2"])


@router.post("/score")
async def score(request: ScoreRequest):
    """
    Score IELTS speaking response directly (v2 - Google AI Studio)
    
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
        
        # Call Google AI
        response_text = google_ai_service.chat(
            messages=messages,
            temperature=0.3,
            max_output_tokens=2048
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
    Score IELTS speaking response using Google AI Studio (v2)
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
        
        # Call Google AI
        model = payload.model or None
        response_text = google_ai_service.chat(
            messages=messages,
            model=model,
            temperature=0.3,
            max_output_tokens=2048
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
    """Generate IELTS Speaking topics with related questions (v2 - Google AI Studio)"""
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
        
        response_text = google_ai_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            max_output_tokens=2048
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
    """Generate IELTS Speaking questions with sample answers, vocabulary, and structures (v2 - Google AI Studio)"""
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
        
        response_text = google_ai_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            max_output_tokens=4096
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


@router.post("/generate/answers")
async def generate_answers(request: AnswersRequest):
    """Generate sample answers for IELTS Speaking questions (v2 - Google AI Studio)"""
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
        
        response_text = google_ai_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            max_output_tokens=4096
        )
        
        result = extract_json_from_generate_response(response_text)
        
        # Handle alternative field names (LLM might use different names)
        if "sampleAnswer" in result and "answer" not in result:
            result["answer"] = result["sampleAnswer"]
        if "sample_answer" in result and "answer" not in result:
            result["answer"] = result["sample_answer"]
        
        # Validate that answer field exists
        if "answer" not in result:
            returned_fields = list(result.keys())
            raise HTTPException(
                status_code=500, 
                detail=f"Invalid response format: missing 'answer' field. Returned fields: {returned_fields}. Response preview: {str(result)[:500]}"
            )
        
        # Return only the answer field
        return {"answer": result["answer"]}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating answers: {str(e)}"
        )


@router.post("/generate/structures", response_model=StructuresResponse)
async def generate_structures(request: StructuresRequest):
    """Generate useful sentence structures for IELTS Speaking (v2 - Google AI Studio)"""
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
        
        response_text = google_ai_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            max_output_tokens=2048
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
    """Generate vocabulary lists with definitions, examples, and pronunciation (v2 - Google AI Studio)"""
    try:
        # Build prompt
        vocabulary_count = request.count or 10
        user_prompt = f"""You are generating a vocabulary list for IELTS Speaking preparation.

Question: {request.question}
Target Band Score: {request.targetBand or 7.0}
Required Number of Vocabulary Items: {vocabulary_count}

CRITICAL REQUIREMENTS:
1. You MUST generate EXACTLY {vocabulary_count} vocabulary items - no more, no less.
2. Each item must be relevant to answering the question.
3. Vocabulary should be appropriate for band {request.targetBand or 7.0} level.
4. Include a mix of single words, phrases, and idioms.

For EACH of the {vocabulary_count} items, provide:
- word: The vocabulary item (word, phrase, or idiom)
- definition: Clear definition
- example: Example sentence related to the question
- pronunciation: IPA pronunciation guide

You MUST return a JSON object with a "vocabulary" array containing EXACTLY {vocabulary_count} items.

Example format (showing first 2 items, but you need {vocabulary_count}):
{{
    "vocabulary": [
        {{
            "word": "lend a hand",
            "definition": "An idiom meaning to help someone with something.",
            "example": "I saw my elderly neighbour struggling with his groceries, so I immediately offered to lend a hand.",
            "pronunciation": "/lɛnd ə hænd/"
        }},
        {{
            "word": "compassionate",
            "definition": "Feeling or showing sympathy and concern for others.",
            "example": "She is a very compassionate person who always helps those in need.",
            "pronunciation": "/kəmˈpæʃənət/"
        }}
        ... (you must include {vocabulary_count} total items in the array)
    ]
}}

REMEMBER: The vocabulary array MUST contain EXACTLY {vocabulary_count} items. Count them before returning."""
        
        system_message = f"You are an expert IELTS English teacher. Your task is to generate EXACTLY {vocabulary_count} vocabulary items in JSON format. You MUST count the items and ensure there are exactly {vocabulary_count} items in the vocabulary array. Return ONLY valid JSON, no explanations, no additional text before or after the JSON."
        
        # Increase max_output_tokens based on count to ensure enough space for all items
        # Estimate: ~200 tokens per vocabulary item
        estimated_tokens = max(2048, vocabulary_count * 200)
        
        # Use lower temperature for more consistent, structured output
        # Retry up to 2 times if we don't get enough items
        max_retries = 2
        for attempt in range(max_retries + 1):
            response_text = google_ai_service.generate(
                system_message=system_message,
                user_prompt=user_prompt,
                temperature=0.3 if attempt == 0 else 0.5,  # Lower temperature for first attempt
                max_output_tokens=min(estimated_tokens, 8192)  # Cap at 8192 (max for some models)
            )
            
            result = extract_json_from_generate_response(response_text)
            
            # Check if we got enough items
            if "vocabulary" in result and isinstance(result["vocabulary"], list):
                actual_count = len(result["vocabulary"])
                if actual_count >= vocabulary_count:
                    break  # Got enough items, exit retry loop
                elif attempt < max_retries:
                    # Not enough items, retry with adjusted prompt
                    user_prompt = f"""{user_prompt}

IMPORTANT: The previous response only had {actual_count} items, but you need to generate EXACTLY {vocabulary_count} items. Please try again and ensure you generate all {vocabulary_count} vocabulary items."""
                    continue
            
            # If we reach here and it's not the last attempt, continue retry
            if attempt < max_retries:
                continue
            
            # Last attempt, break and use what we got
            break
        
        # Handle case where Google AI returns vocabulary items directly instead of wrapped in "vocabulary" array
        if "vocabulary" not in result:
            # Check if result has vocabulary item fields (word, definition, example, pronunciation)
            if all(key in result for key in ["word", "definition", "example"]):
                # Single vocabulary item returned, wrap it in array
                result = {"vocabulary": [result]}
            # Check if result is a list of vocabulary items
            elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                # Check if first item has vocabulary fields
                if all(key in result[0] for key in ["word", "definition", "example"]):
                    result = {"vocabulary": result}
                else:
                    # Provide more helpful error message
                    returned_fields = list(result[0].keys()) if result else []
                    response_preview = str(result)[:1000] if len(str(result)) > 1000 else str(result)
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Invalid response format: missing 'vocabulary' field. Returned fields: {returned_fields}. Response preview: {response_preview}"
                    )
            else:
                # Provide more helpful error message
                returned_fields = list(result.keys()) if isinstance(result, dict) else []
                response_preview = str(result)[:1000] if len(str(result)) > 1000 else str(result)
                raise HTTPException(
                    status_code=500, 
                    detail=f"Invalid response format: missing 'vocabulary' field. Returned fields: {returned_fields}. Response preview: {response_preview}"
                )
        
        # Validate vocabulary count
        if "vocabulary" in result and isinstance(result["vocabulary"], list):
            actual_count = len(result["vocabulary"])
            if actual_count < vocabulary_count:
                # Log warning - Google AI didn't return enough items
                # We'll return what we got, but this could be improved with retry logic
                pass  # For now, just return what we got
        
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
    Generic text generation endpoint for various tasks (FALLBACK/PLAYGROUND) (v2 - Google AI Studio)
    
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
        
        response_text = google_ai_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            max_output_tokens=2048
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
    Correct grammar for a transcription (v2 - Google AI Studio)
    
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
        # Validate input
        if not request.transcription or request.transcription.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="Transcription cannot be empty"
            )
        
        transcription = request.transcription.strip()
        
        # Build prompt
        question_context = ""
        if request.textQuestion and request.textQuestion.strip():
            question_context = f"\n\nContext/Question: {request.textQuestion.strip()}"
        
        user_prompt = f"""You are an expert English grammar teacher. Your task is to correct ALL grammar errors in the COMPLETE transcription provided below.

TRANSCRIPTION TO CORRECT (you must process ALL of it):
{transcription}{question_context}

CRITICAL REQUIREMENTS - You MUST follow ALL these rules:

1. FIX ALL grammatical errors in the ENTIRE transcription including:
   - Subject-verb agreement errors
   - Wrong verb tenses (past, present, future)
   - Missing or incorrect articles (a, an, the)
   - Incorrect prepositions (for, to, at, in, on, etc.)
   - Punctuation errors (periods, commas, apostrophes, etc.)
   - Word repetition and redundancy
   - Sentence structure issues
   - Unnatural word order
   - Missing or incorrect conjunctions
   - Spelling errors

2. Process the COMPLETE transcription - do not truncate or skip any part
3. Maintain the EXACT original meaning and context
4. Keep the same style and tone (informal/formal)
5. Make the corrected version natural, fluent, and native-like
6. Document EVERY single correction made in the corrections array
7. ALWAYS return complete, valid JSON with ALL required fields

Return JSON in this EXACT format with NO ADDITIONAL TEXT:
{{
    "original": "the complete original transcription exactly as provided above",
    "corrected": "the complete corrected version with ALL errors fixed",
    "corrections": [
        {{
            "original": "exact incorrect word/phrase from original",
            "corrected": "corrected word/phrase",
            "reason": "brief explanation"
        }}
    ],
    "explanation": "A comprehensive summary of all corrections made"
}}

EXAMPLES OF CORRECTIONS:
- "Yes. I like it" → "Yes, I like it" (Fixed punctuation - period should be comma)
- "I have an experience" → "I have experience" (Removed unnecessary article)
- "Well, I for example, I" → "Well, for example, I" (Removed redundant pronoun)
- "studied for English" → "studied English" (Removed incorrect preposition)
- "I go yesterday" → "I went yesterday" (Fixed verb tense)

MANDATORY VALIDATION RULES:
1. The "original" field MUST contain the COMPLETE original transcription (not truncated)
2. The "corrected" field MUST contain the COMPLETE corrected version (same length or similar)
3. The "corrections" array MUST be a valid array (can be empty [] if no corrections)
4. The "explanation" field MUST be a non-empty string describing what was changed
5. If NO corrections are needed, return: corrections=[], explanation="No corrections needed. The transcription is grammatically correct."
6. Return ONLY valid JSON - no text before or after the JSON object"""
        
        system_message = f"You are an expert English grammar teacher specializing in correcting spoken {request.language or 'English'} transcriptions. Your job is to identify and fix ALL grammatical errors while preserving the original meaning. You MUST return ONLY valid JSON format with no additional text before or after. Ensure the response contains the complete original and corrected text, not truncated versions."
        
        # Calculate appropriate max_output_tokens based on input length
        # Rule: output should be at least 2x input length to allow for complete correction + metadata
        input_length = len(transcription)
        min_tokens = 3072  # Increased minimum
        estimated_tokens = max(min_tokens, int(input_length * 3.5))  # Increased multiplier
        max_tokens = min(estimated_tokens, 8192)  # Cap at model limit
        
        # Retry logic for incomplete responses
        max_retries = 2
        result = None
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # Adjust prompt for retry attempts
                current_prompt = user_prompt
                if attempt > 0:
                    current_prompt = f"""RETRY ATTEMPT {attempt + 1}: The previous response was incomplete or truncated.
You MUST return the COMPLETE corrected text, not a truncated version.

{user_prompt}"""
                
                response_text = google_ai_service.generate(
                    system_message=system_message,
                    user_prompt=current_prompt,
                    temperature=0.2 if attempt == 0 else 0.3,  # Slightly higher temp on retry
                    max_output_tokens=max_tokens
                )
                
                # Extract JSON from response
                result = extract_json_from_generate_response(response_text)
                
                # Quick validation - check if corrected text seems complete
                if result.get("corrected") and len(result["corrected"]) >= len(transcription) * 0.6:
                    # Response seems complete enough
                    break
                else:
                    # Response seems incomplete, try again
                    if attempt < max_retries:
                        corrected_len = len(result.get("corrected", ""))
                        last_error = f"Incomplete response on attempt {attempt + 1}: corrected text only {corrected_len} chars"
                        continue
                    
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    continue
                else:
                    raise
        
        if result is None:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get complete response after {max_retries + 1} attempts. Last error: {last_error}"
            )
        
        # VALIDATION STEP 1: Check for required fields
        required_fields = ["original", "corrected"]
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            raise HTTPException(
                status_code=500,
                detail=f"AI response missing required fields: {missing_fields}. This is an internal error. Please try again."
            )
        
        # VALIDATION STEP 2: Ensure all fields are proper types and not null
        # Handle original field
        if not result.get("original") or not isinstance(result["original"], str):
            result["original"] = transcription
        else:
            # Ensure original is not truncated
            result["original"] = result["original"].strip()
            if len(result["original"]) < len(transcription) * 0.8:
                # Original seems truncated, use input transcription
                result["original"] = transcription
        
        # Handle corrected field
        if not result.get("corrected") or not isinstance(result["corrected"], str):
            # If corrected is missing or invalid, use original
            result["corrected"] = transcription
        else:
            result["corrected"] = result["corrected"].strip()
        
        # VALIDATION STEP 3: Ensure corrections is always a valid list
        if "corrections" not in result or result["corrections"] is None:
            result["corrections"] = []
        elif not isinstance(result["corrections"], list):
            # If corrections is not a list, convert to empty list
            result["corrections"] = []
        else:
            # Validate each correction item
            valid_corrections = []
            for correction in result["corrections"]:
                if isinstance(correction, dict):
                    # Ensure all correction fields are strings
                    if "original" in correction and "corrected" in correction and "reason" in correction:
                        valid_corrections.append({
                            "original": str(correction.get("original", "")),
                            "corrected": str(correction.get("corrected", "")),
                            "reason": str(correction.get("reason", ""))
                        })
            result["corrections"] = valid_corrections
        
        # VALIDATION STEP 4: Ensure explanation is always a non-empty string
        if "explanation" not in result or result["explanation"] is None or not isinstance(result["explanation"], str):
            # Generate explanation based on corrections
            if len(result["corrections"]) > 0:
                result["explanation"] = f"Made {len(result['corrections'])} correction(s) to improve grammar and clarity."
            elif result["original"] != result["corrected"]:
                result["explanation"] = "Made minor adjustments to improve grammar and naturalness."
            else:
                result["explanation"] = "No corrections needed. The transcription is grammatically correct."
        else:
            result["explanation"] = result["explanation"].strip()
            if not result["explanation"]:
                # Empty explanation
                if len(result["corrections"]) > 0:
                    result["explanation"] = f"Made {len(result['corrections'])} correction(s) to improve grammar."
                elif result["original"] != result["corrected"]:
                    result["explanation"] = "Made minor adjustments for better grammar."
                else:
                    result["explanation"] = "No corrections needed. The transcription is grammatically correct."
        
        # VALIDATION STEP 5: Check for completeness - corrected text should not be too short
        original_len = len(result["original"])
        corrected_len = len(result["corrected"])
        
        # If corrected is significantly shorter than original (>40% shorter), it might be truncated
        if original_len > 30 and corrected_len < original_len * 0.6:
            # Try one more time with a simplified prompt
            try:
                simplified_prompt = f"""Fix the grammar errors in this text and return the COMPLETE corrected version:

TEXT: {transcription}

Return ONLY JSON:
{{
    "original": "full original text",
    "corrected": "full corrected text",
    "corrections": [],
    "explanation": "summary of changes"
}}

The corrected text MUST be the SAME LENGTH or longer than the original. Do not truncate."""
                
                response_text = google_ai_service.generate(
                    system_message="You are a grammar correction expert. Return ONLY complete, valid JSON.",
                    user_prompt=simplified_prompt,
                    temperature=0.1,
                    max_output_tokens=max_tokens
                )
                
                fallback_result = extract_json_from_generate_response(response_text)
                
                # Check if fallback is better
                if fallback_result.get("corrected") and len(fallback_result["corrected"]) >= original_len * 0.6:
                    result = fallback_result
                    # Re-validate this result below
                else:
                    # Even fallback failed, return original as corrected
                    result["corrected"] = transcription
                    result["corrections"] = []
                    result["explanation"] = "Unable to process corrections. Returning original text unchanged."
                    
            except:
                # Fallback failed, return original as corrected
                result["corrected"] = transcription
                result["corrections"] = []
                result["explanation"] = "Unable to process corrections. Returning original text unchanged."
            
            # Recalculate lengths after potential fallback
            corrected_len = len(result["corrected"])
        
        # VALIDATION STEP 6: Final consistency check
        # If corrections array is not empty but explanation says no corrections, fix it
        if len(result["corrections"]) > 0 and "no correction" in result["explanation"].lower():
            result["explanation"] = f"Made {len(result['corrections'])} correction(s) including grammar, punctuation, and style improvements."
        
        # If original and corrected are the same but there are corrections listed, this is inconsistent
        if result["original"] == result["corrected"] and len(result["corrections"]) > 0:
            # Clear corrections since nothing actually changed
            result["corrections"] = []
            result["explanation"] = "No corrections needed. The transcription is grammatically correct."
        
        # FINAL SAFETY CHECK: Ensure all required fields are present and valid
        final_result = {
            "original": str(result.get("original", transcription)),
            "corrected": str(result.get("corrected", transcription)),
            "corrections": result.get("corrections", []) if isinstance(result.get("corrections"), list) else [],
            "explanation": str(result.get("explanation", "Grammar correction completed.")) if result.get("explanation") else "Grammar correction completed."
        }
        
        # Ensure strings are not empty
        if not final_result["original"]:
            final_result["original"] = transcription
        if not final_result["corrected"]:
            final_result["corrected"] = transcription
        if not final_result["explanation"]:
            if len(final_result["corrections"]) > 0:
                final_result["explanation"] = f"Made {len(final_result['corrections'])} correction(s)."
            else:
                final_result["explanation"] = "No corrections needed."
        
        # Return validated response
        return GrammarCorrectionResponse(**final_result)
        
    except HTTPException:
        raise
    except Exception as e:
        # Log the error details for debugging
        error_detail = f"Error correcting grammar: {str(e)}"
        if hasattr(e, '__traceback__'):
            import traceback
            error_detail += f"\n{traceback.format_exc()}"
        
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@router.post("/improve", response_model=ImproveResponse)
async def improve_sentence(request: ImproveRequest):
    """
    Improve a sentence for IELTS Speaking (v2 - Google AI Studio)
    
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
    "original": "the original sentence",
    "improved": "the improved sentence",
    "improvements": [
        {{
            "type": "grammar|vocabulary|structure|fluency",
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
        
        # Increase max_output_tokens significantly for long transcriptions
        # Estimate tokens needed: ~1.3x the input length + suggestions
        input_length = len(request.transcription)
        estimated_tokens = max(4096, int(input_length * 1.5) + 1000)  # Extra for suggestions
        
        response_text = google_ai_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.3,
            max_output_tokens=min(estimated_tokens, 8192)  # Cap at 8192 (max for most models)
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
                detail=f"Response appears incomplete. Original length: {original_length} chars, Improved length: {improved_length} chars. The improved text should be similar length to the original. Please ensure the AI processes the ENTIRE transcription."
            )
        
        return ImproveResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error improving sentence: {str(e)}"
        )


@router.get("/models")
async def list_models():
    """
    List all available Google AI models (v2)
    
    Returns a list of models that support generateContent method.
    """
    try:
        models = google_ai_service.list_models()
        return {
            "models": models,
            "count": len(models),
            "default_model": google_ai_service.model_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing models: {str(e)}"
        )
