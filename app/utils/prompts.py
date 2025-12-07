"""Prompt building utilities for IELTS evaluation and generation"""


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

