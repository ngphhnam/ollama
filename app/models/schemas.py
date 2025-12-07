from pydantic import BaseModel
from typing import Optional, List


class Message(BaseModel):
    role: str
    content: str


class ChatPayload(BaseModel):
    model: str
    messages: List[Message]
    format: Optional[dict] = None


class ScoreRequest(BaseModel):
    """Request model for direct scoring endpoint"""
    transcription: str
    questionText: Optional[str] = None
    topic: Optional[str] = "General"
    level: Optional[str] = "intermediate"


class QuestionItem(BaseModel):
    """Model for a single question item"""
    name: str
    questions: List[str]


class TopicsRequest(BaseModel):
    """Request model for topics generation"""
    partNumber: Optional[int] = 1
    difficultyLevel: Optional[str] = "intermediate"
    count: Optional[int] = 5
    topicCategory: Optional[str] = None
    prompt: Optional[str] = None  # Optional custom prompt


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


class GrammarCorrectionRequest(BaseModel):
    """Request model for grammar correction"""
    transcription: str
    textQuestion: Optional[str] = None
    language: Optional[str] = "en"  # Language code, default to English


class GrammarCorrectionResponse(BaseModel):
    """Response model for grammar correction"""
    original: str
    corrected: str
    corrections: Optional[List[dict]] = None  # List of corrections made
    explanation: Optional[str] = None  # Explanation of corrections


class ImproveRequest(BaseModel):
    """Request model for sentence improvement"""
    transcription: str
    questionText: Optional[str] = None
    language: Optional[str] = "en"  # Language code, default to English


class ImproveResponse(BaseModel):
    """Response model for sentence improvement"""
    original: str
    improved: str
    improvements: Optional[List[dict]] = None  # List of improvements made
    explanation: Optional[str] = None  # Explanation of improvements
    vocabularySuggestions: Optional[List[VocabularyItem]] = None  # Suggested vocabulary
    structureSuggestions: Optional[List[StructureItem]] = None  # Suggested structures

