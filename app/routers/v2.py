"""API v2 routes sử dụng Google AI Studio"""
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
    Chấm điểm phản hồi IELTS speaking trực tiếp (v2 - Google AI Studio)
    
    Endpoint đơn giản nhận transcription, topic, và level trực tiếp.
    Tự động bao gồm sửa ngữ pháp khi phát hiện lỗi ngữ pháp.
    """
    try:
        # Xây dựng prompt chuyên biệt cho IELTS
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
        
        # Gọi Google AI
        response_text = google_ai_service.chat(
            messages=messages,
            temperature=0.3,
            max_output_tokens=2048
        )
        
        # Trích xuất JSON từ response
        result = extract_json_from_response(response_text)
        
        # Xác thực và đặt giá trị mặc định
        band_score = float(result.get("bandScore", 6.5))
        pronunciation_score = float(result.get("pronunciationScore", 6.0))
        grammar_score = float(result.get("grammarScore", 6.5))
        vocabulary_score = float(result.get("vocabularyScore", 6.0))
        fluency_score = float(result.get("fluencyScore", 6.5))
        overall_feedback = result.get("overallFeedback", "Evaluation completed.")
        
        # Giới hạn điểm số trong khoảng hợp lệ
        def clamp_score(score):
            return max(0.0, min(9.0, float(score)))
        
        clamped_grammar_score = clamp_score(grammar_score)
        
        # Chuẩn bị response
        response = {
            "bandScore": clamp_score(band_score),
            "pronunciationScore": clamp_score(pronunciation_score),
            "grammarScore": clamped_grammar_score,
            "vocabularyScore": clamp_score(vocabulary_score),
            "fluencyScore": clamp_score(fluency_score),
            "overallFeedback": overall_feedback
        }
        
        # Tự động bao gồm sửa ngữ pháp nếu được yêu cầu
        # Mặc định là True - luôn bao gồm sửa ngữ pháp để giúp người dùng cải thiện
        should_include_grammar = request.includeGrammarCorrection if request.includeGrammarCorrection is not None else True
        
        # Luôn bao gồm sửa ngữ pháp khi should_include_grammar là True (hành vi mặc định)
        # Điều này đảm bảo người dùng luôn nhận được sửa ngữ pháp khi có lỗi, giúp họ học hỏi
        if should_include_grammar:
            try:
                # Gọi sửa ngữ pháp nội bộ
                grammar_request = GrammarCorrectionRequest(
                    transcription=request.transcription,
                    textQuestion=request.questionText,
                    language="en"
                )
                
                # Gọi hàm sửa ngữ pháp
                grammar_result = await correct_grammar(grammar_request)
                
                # Thêm sửa ngữ pháp vào response
                response["grammarCorrection"] = {
                    "original": grammar_result.original,
                    "corrected": grammar_result.corrected,
                    "corrections": grammar_result.corrections or [],
                    "explanation": grammar_result.explanation
                }
                response["correctedTranscription"] = grammar_result.corrected
            except Exception as grammar_error:
                # Nếu sửa ngữ pháp thất bại, ghi log nhưng không làm thất bại toàn bộ request
                # Chỉ bao gồm null cho sửa ngữ pháp
                response["grammarCorrection"] = None
                response["correctedTranscription"] = None
        else:
            # Không cần hoặc không yêu cầu sửa ngữ pháp
            response["grammarCorrection"] = None
            response["correctedTranscription"] = None
        
        return response
        
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
    Chấm điểm phản hồi IELTS speaking sử dụng Google AI Studio (v2)
    """
    try:
        # Trích xuất transcription, topic, và level từ messages
        user_message = None
        system_message = None
        
        for msg in payload.messages:
            if msg.role == "user":
                user_message = msg.content
            elif msg.role == "system":
                system_message = msg.content
        
        # Nếu không có prompt rõ ràng, xây dựng một từ transcription
        if not system_message or "IELTS" not in system_message:
            # Thử trích xuất transcription từ user message
            transcription = user_message or ""
            topic = "General"
            level = "intermediate"
            
            # Xây dựng prompt chuyên biệt cho IELTS
            prompt = build_ielts_prompt(transcription, "", topic, level)
            messages = [
                {"role": "system", "content": "You are an expert IELTS speaking examiner. Always return valid JSON only."},
                {"role": "user", "content": prompt}
            ]
        else:
            # Sử dụng messages được cung cấp
            messages = [{"role": msg.role, "content": msg.content} for msg in payload.messages]
        
        # Gọi Google AI
        model = payload.model or None
        response_text = google_ai_service.chat(
            messages=messages,
            model=model,
            temperature=0.3,
            max_output_tokens=2048
        )
        
        # Trích xuất JSON từ response
        result = extract_json_from_response(response_text)
        
        # Xác thực và đặt giá trị mặc định
        band_score = float(result.get("bandScore", 6.5))
        pronunciation_score = float(result.get("pronunciationScore", 6.0))
        grammar_score = float(result.get("grammarScore", 6.5))
        vocabulary_score = float(result.get("vocabularyScore", 6.0))
        fluency_score = float(result.get("fluencyScore", 6.5))
        overall_feedback = result.get("overallFeedback", "Evaluation completed.")
        
        # Giới hạn điểm số trong khoảng hợp lệ
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
    """Tạo chủ đề IELTS Speaking kèm câu hỏi liên quan (v2 - Google AI Studio)"""
    try:
        # Xây dựng prompt
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
        
        # Xác thực và trả về
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
    """Tạo câu hỏi IELTS Speaking kèm câu trả lời mẫu, từ vựng, và cấu trúc (v2 - Google AI Studio)"""
    try:
        # Xây dựng prompt
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
        
        # Xác thực và trả về
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
    """Tạo câu trả lời mẫu cho câu hỏi IELTS Speaking (v2 - Google AI Studio)"""
    try:
        # Xây dựng prompt
        user_prompt = f"""Generate a concise sample answer for this IELTS Speaking Part {request.partNumber or 2} question:

Question: {request.question}

Requirements:
- Target band score: {request.targetBand or 7.0}
- Answer should be SHORT and CONCISE (about 30-60 seconds of speaking, NOT 2-3 minutes)
- Include advanced vocabulary and complex structures appropriate for the target band
- Keep the answer natural, fluent, and to the point
- Do NOT make it too long or verbose

CRITICAL: You MUST return ONLY a JSON object with ONE field called "answer". Do NOT include vocabulary, structures, keyPoints, or any other fields. Only return the answer text.

Return JSON in this EXACT format (ONLY the answer field):
{{
    "answer": "A concise sample answer (30-60 seconds of speaking). Keep it short and focused."
}}

IMPORTANT: 
- Return ONLY valid JSON
- The JSON must contain ONLY the "answer" field
- Do not include any text before or after the JSON
- The answer should be SHORT and CONCISE, not lengthy"""
        
        system_message = "You are an expert IELTS speaking coach. Generate concise, high-quality sample answers. You MUST return ONLY a JSON object with a single 'answer' field containing a SHORT answer text. Do not include any other fields. Keep answers brief and focused."
        
        response_text = google_ai_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.7,
            max_output_tokens=1024  # Giảm vì chỉ cần câu trả lời ngắn
        )
        
        result = extract_json_from_generate_response(response_text)
        
        # Xử lý tên field thay thế (LLM có thể sử dụng tên khác)
        if "sampleAnswer" in result and "answer" not in result:
            result["answer"] = result["sampleAnswer"]
        if "sample_answer" in result and "answer" not in result:
            result["answer"] = result["sample_answer"]
        
        # Kiểm tra xem LLM có trả về vocabulary items thay vì answer không
        # Điều này có thể xảy ra nếu LLM hiểu nhầm prompt
        if "answer" not in result:
            # Kiểm tra xem result có chứa cấu trúc vocabulary item không
            if all(key in result for key in ["word", "definition", "example", "pronunciation"]):
                # Một vocabulary item được trả về - xây dựng câu trả lời ngắn từ nó
                vocab_example = result.get("example", "")
                result["answer"] = vocab_example if vocab_example else f"I would like to discuss {result.get('word', 'this topic')}."
            elif "vocabulary" in result and isinstance(result["vocabulary"], list) and len(result["vocabulary"]) > 0:
                # Mảng vocabulary được trả về - xây dựng câu trả lời ngắn từ ví dụ vocabulary đầu tiên
                vocab_items = result["vocabulary"]
                if len(vocab_items) > 0 and isinstance(vocab_items[0], dict) and "example" in vocab_items[0]:
                    result["answer"] = vocab_items[0].get("example", "")
                else:
                    result["answer"] = f"I would approach this question by considering the key aspects related to {request.question}."
            else:
                # Không có answer và không có cấu trúc vocabulary - thử trích xuất bất kỳ nội dung text nào
                returned_fields = list(result.keys())
                
                # Thử xây dựng answer từ bất kỳ text field nào có sẵn
                possible_answer = None
                for field in ["content", "text", "response", "sampleAnswer", "sample_answer"]:
                    if field in result and isinstance(result[field], str) and len(result[field]) > 10:
                        possible_answer = result[field]
                        break
                
                if possible_answer:
                    result["answer"] = possible_answer
                else:
                    # Biện pháp cuối cùng: tạo một câu trả lời chung ngắn
                    result["answer"] = f"I would approach this question by considering the main points related to the topic."
        
        # Xác thực rằng field answer tồn tại và không rỗng
        if "answer" not in result or not result["answer"] or len(result["answer"].strip()) < 10:
            returned_fields = list(result.keys())
            raise HTTPException(
                status_code=500, 
                detail=f"Invalid response format: missing or invalid 'answer' field. Returned fields: {returned_fields}. Response preview: {str(result)[:500]}"
            )
        
        # Cắt ngắn answer nếu quá dài (giới hạn ~500 từ cho câu trả lời ngắn gọn)
        answer_text = result["answer"].strip()
        words = answer_text.split()
        if len(words) > 500:
            answer_text = " ".join(words[:500]) + "..."
        
        # Chỉ trả về field answer
        return {"answer": answer_text}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating answers: {str(e)}"
        )


@router.post("/generate/structures", response_model=StructuresResponse)
async def generate_structures(request: StructuresRequest):
    """Tạo cấu trúc câu hữu ích cho IELTS Speaking (v2 - Google AI Studio)"""
    try:
        # Xây dựng prompt
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
        
        # Xác thực và trả về
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
    """Tạo danh sách từ vựng kèm định nghĩa, ví dụ, và phát âm (v2 - Google AI Studio)"""
    try:
        # Xây dựng prompt
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
        
        # Tăng max_output_tokens dựa trên count để đảm bảo đủ không gian cho tất cả items
        # Ước tính: ~200 tokens mỗi vocabulary item
        estimated_tokens = max(2048, vocabulary_count * 200)
        
        # Sử dụng temperature thấp hơn để output nhất quán và có cấu trúc hơn
        # Thử lại tối đa 2 lần nếu không có đủ items
        max_retries = 2
        for attempt in range(max_retries + 1):
            response_text = google_ai_service.generate(
                system_message=system_message,
                user_prompt=user_prompt,
                temperature=0.3 if attempt == 0 else 0.5,  # Temperature thấp hơn cho lần thử đầu tiên
                max_output_tokens=min(estimated_tokens, 8192)  # Giới hạn ở 8192 (tối đa cho một số models)
            )
            
            result = extract_json_from_generate_response(response_text)
            
            # Kiểm tra xem đã có đủ items chưa
            if "vocabulary" in result and isinstance(result["vocabulary"], list):
                actual_count = len(result["vocabulary"])
                if actual_count >= vocabulary_count:
                    break  # Đã có đủ items, thoát vòng lặp retry
                elif attempt < max_retries:
                    # Chưa đủ items, thử lại với prompt đã điều chỉnh
                    user_prompt = f"""{user_prompt}

IMPORTANT: The previous response only had {actual_count} items, but you need to generate EXACTLY {vocabulary_count} items. Please try again and ensure you generate all {vocabulary_count} vocabulary items."""
                    continue
            
            # Nếu đến đây và không phải lần thử cuối, tiếp tục retry
            if attempt < max_retries:
                continue
            
            # Lần thử cuối, dừng và sử dụng những gì đã có
            break
        
        # Xử lý trường hợp Google AI trả về vocabulary items trực tiếp thay vì bọc trong mảng "vocabulary"
        if "vocabulary" not in result:
            # Kiểm tra xem result có các field vocabulary item không (word, definition, example, pronunciation)
            if all(key in result for key in ["word", "definition", "example"]):
                # Một vocabulary item được trả về, bọc nó trong mảng
                result = {"vocabulary": [result]}
            # Kiểm tra xem result có phải là danh sách vocabulary items không
            elif isinstance(result, list) and len(result) > 0 and isinstance(result[0], dict):
                # Kiểm tra xem item đầu tiên có các field vocabulary không
                if all(key in result[0] for key in ["word", "definition", "example"]):
                    result = {"vocabulary": result}
                else:
                    # Cung cấp thông báo lỗi hữu ích hơn
                    returned_fields = list(result[0].keys()) if result else []
                    response_preview = str(result)[:1000] if len(str(result)) > 1000 else str(result)
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Invalid response format: missing 'vocabulary' field. Returned fields: {returned_fields}. Response preview: {response_preview}"
                    )
            else:
                # Cung cấp thông báo lỗi hữu ích hơn
                returned_fields = list(result.keys()) if isinstance(result, dict) else []
                response_preview = str(result)[:1000] if len(str(result)) > 1000 else str(result)
                raise HTTPException(
                    status_code=500, 
                    detail=f"Invalid response format: missing 'vocabulary' field. Returned fields: {returned_fields}. Response preview: {response_preview}"
                )
        
        # Xác thực số lượng vocabulary
        if "vocabulary" in result and isinstance(result["vocabulary"], list):
            actual_count = len(result["vocabulary"])
            if actual_count < vocabulary_count:
                # Ghi cảnh báo - Google AI không trả về đủ items
                # Sẽ trả về những gì đã có, nhưng điều này có thể được cải thiện với retry logic
                pass  # Hiện tại, chỉ trả về những gì đã có
        
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
    Endpoint tạo text chung cho các tác vụ khác nhau (FALLBACK/PLAYGROUND) (v2 - Google AI Studio)
    
    ⚠️ LƯU Ý: Đây là endpoint fallback/playground để thử nghiệm.
    Để sử dụng trong production, vui lòng sử dụng các endpoint chuyên biệt.
    """
    try:
        # Xây dựng system message dựa trên loại task
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
        
        # Thêm context vào prompt nếu được cung cấp
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
    Sửa ngữ pháp cho một transcription (v2 - Google AI Studio)
    
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
        # Xác thực input
        if not request.transcription or request.transcription.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="Transcription cannot be empty"
            )
        
        transcription = request.transcription.strip()
        
        # Xây dựng prompt
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
        
        # Tính toán max_output_tokens phù hợp dựa trên độ dài input
        # Quy tắc: output nên ít nhất gấp 2 lần độ dài input để cho phép sửa đầy đủ + metadata
        input_length = len(transcription)
        min_tokens = 2048
        estimated_tokens = max(min_tokens, int(input_length * 2.5))
        max_tokens = min(estimated_tokens, 8192)  # Cap at model limit
        
        response_text = google_ai_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.2,  # Temperature thấp hơn để sửa chữa nhất quán và chính xác hơn
            max_output_tokens=max_tokens
        )
        
        # Trích xuất JSON từ response
        result = extract_json_from_generate_response(response_text)
        
        # BƯỚC XÁC THỰC 1: Kiểm tra các field bắt buộc
        required_fields = ["original", "corrected"]
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            raise HTTPException(
                status_code=500,
                detail=f"AI response missing required fields: {missing_fields}. This is an internal error. Please try again."
            )
        
        # BƯỚC XÁC THỰC 2: Đảm bảo tất cả các field có kiểu dữ liệu đúng và không null
        # Xử lý field original
        if not result.get("original") or not isinstance(result["original"], str):
            result["original"] = transcription
        else:
            # Đảm bảo original không bị cắt ngắn
            result["original"] = result["original"].strip()
            if len(result["original"]) < len(transcription) * 0.8:
                # Original có vẻ bị cắt ngắn, sử dụng input transcription
                result["original"] = transcription
        
        # Xử lý field corrected
        if not result.get("corrected") or not isinstance(result["corrected"], str):
            # Nếu corrected thiếu hoặc không hợp lệ, sử dụng original
            result["corrected"] = transcription
        else:
            result["corrected"] = result["corrected"].strip()
        
        # BƯỚC XÁC THỰC 3: Đảm bảo corrections luôn là một list hợp lệ
        if "corrections" not in result or result["corrections"] is None:
            result["corrections"] = []
        elif not isinstance(result["corrections"], list):
            # Nếu corrections không phải là list, chuyển đổi thành list rỗng
            result["corrections"] = []
        else:
            # Xác thực từng correction item
            valid_corrections = []
            for correction in result["corrections"]:
                if isinstance(correction, dict):
                    # Đảm bảo tất cả các field correction là strings
                    if "original" in correction and "corrected" in correction and "reason" in correction:
                        valid_corrections.append({
                            "original": str(correction.get("original", "")),
                            "corrected": str(correction.get("corrected", "")),
                            "reason": str(correction.get("reason", ""))
                        })
            result["corrections"] = valid_corrections
        
        # BƯỚC XÁC THỰC 4: Đảm bảo explanation luôn là một string không rỗng
        if "explanation" not in result or result["explanation"] is None or not isinstance(result["explanation"], str):
            # Tạo explanation dựa trên corrections
            if len(result["corrections"]) > 0:
                result["explanation"] = f"Made {len(result['corrections'])} correction(s) to improve grammar and clarity."
            elif result["original"] != result["corrected"]:
                result["explanation"] = "Made minor adjustments to improve grammar and naturalness."
            else:
                result["explanation"] = "No corrections needed. The transcription is grammatically correct."
        else:
            result["explanation"] = result["explanation"].strip()
            if not result["explanation"]:
                # Explanation rỗng
                if len(result["corrections"]) > 0:
                    result["explanation"] = f"Made {len(result['corrections'])} correction(s) to improve grammar."
                elif result["original"] != result["corrected"]:
                    result["explanation"] = "Made minor adjustments for better grammar."
                else:
                    result["explanation"] = "No corrections needed. The transcription is grammatically correct."
        
        # BƯỚC XÁC THỰC 5: Kiểm tra tính đầy đủ - corrected text không nên quá ngắn
        original_len = len(result["original"])
        corrected_len = len(result["corrected"])
        
        # Nếu corrected ngắn hơn đáng kể so với original (>40% ngắn hơn), có thể bị cắt ngắn
        if original_len > 30 and corrected_len < original_len * 0.6:
            raise HTTPException(
                status_code=500,
                detail=f"AI response appears incomplete. Original text: {original_len} characters, Corrected text: {corrected_len} characters. The corrected text seems truncated. Please try again."
            )
        
        # BƯỚC XÁC THỰC 6: Kiểm tra tính nhất quán cuối cùng
        # Nếu mảng corrections không rỗng nhưng explanation nói không có corrections, sửa nó
        if len(result["corrections"]) > 0 and "no correction" in result["explanation"].lower():
            result["explanation"] = f"Made {len(result['corrections'])} correction(s) including grammar, punctuation, and style improvements."
        
        # Nếu original và corrected giống nhau nhưng có corrections được liệt kê, điều này không nhất quán
        if result["original"] == result["corrected"] and len(result["corrections"]) > 0:
            # Xóa corrections vì không có gì thực sự thay đổi
            result["corrections"] = []
            result["explanation"] = "No corrections needed. The transcription is grammatically correct."
        
        # Trả về response đã được xác thực
        return GrammarCorrectionResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        # Ghi log chi tiết lỗi để debug
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
    Cải thiện câu cho IELTS Speaking (v2 - Google AI Studio)
    
    Endpoint này cải thiện câu bằng cách:
    - Sửa lỗi ngữ pháp
    - Sử dụng từ vựng nâng cao hơn
    - Cải thiện cấu trúc câu
    - Làm cho nó tự nhiên và trôi chảy hơn
    
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
        # Xây dựng prompt
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
        
        # Tăng max_output_tokens đáng kể cho transcriptions dài
        # Ước tính tokens cần: ~1.3x độ dài input + suggestions
        input_length = len(request.transcription)
        estimated_tokens = max(4096, int(input_length * 1.5) + 1000)  # Extra for suggestions
        
        response_text = google_ai_service.generate(
            system_message=system_message,
            user_prompt=user_prompt,
            temperature=0.3,
            max_output_tokens=min(estimated_tokens, 8192)  # Cap at 8192 (max for most models)
        )
        
        result = extract_json_from_generate_response(response_text)
        
        # Xác thực các field bắt buộc
        required_fields = ["original", "improved"]
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            returned_fields = list(result.keys())
            raise HTTPException(
                status_code=500,
                detail=f"Invalid response format: missing fields {missing_fields}. Returned fields: {returned_fields}"
            )
        
        # Đảm bảo original và improved được đặt
        if "original" not in result:
            result["original"] = request.transcription
        if "improved" not in result:
            result["improved"] = request.transcription
        
        # Xác thực rằng improved text có độ dài hợp lý (ít nhất 50% của original)
        # Điều này giúp phát hiện các trường hợp chỉ xử lý một phần nhỏ
        original_length = len(result.get("original", ""))
        improved_length = len(result.get("improved", ""))
        
        if original_length > 100 and improved_length < original_length * 0.5:
            # Improved text quá ngắn - có thể chỉ xử lý một phần
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
    Liệt kê tất cả các Google AI models có sẵn (v2)
    
    Trả về danh sách các models hỗ trợ phương thức generateContent.
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
