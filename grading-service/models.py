from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class UnderstandingLevel(str, Enum):
    excellent = "отличный"
    good = "хороший"
    average = "средний"
    weak = "слабый"
    critical = "критический"


class ErrorType(str, Enum):
    conceptual = "концептуальные"
    computational = "вычислительные"
    logical = "логические"
    factual = "фактические"
    incomplete = "неполные ответы"
    language = "языковые/грамматические"


class GradingRequest(BaseModel):
    extracted_text: str = Field(description="Весь текст ДЗ от OCR сервиса")
    subject: str = Field(description="Предмет: математика, физика, история, химия и т.д.")
    student_id: Optional[str] = Field(default=None, description="ID студента для аналитики")
    assignment_id: Optional[str] = Field(default=None, description="ID задания")


class ProblemResult(BaseModel):
    problem_number: int
    problem_text: str
    student_answer: str
    score: int = Field(ge=0, le=100)
    feedback: str
    correct: bool
    topics: List[str] = Field(description="Темы которые затрагивает задача")
    error_types: List[ErrorType] = Field(default=[], description="Типы ошибок если есть")


class GradingResult(BaseModel):
    student_id: Optional[str]
    assignment_id: Optional[str]
    subject: str
    total_score: int = Field(ge=0, le=100)
    understanding_level: UnderstandingLevel
    problems: List[ProblemResult]
    weak_topics: List[str] = Field(description="Темы где студент слабый")
    strong_topics: List[str] = Field(description="Темы где студент сильный")
    error_types: List[ErrorType] = Field(description="Преобладающие типы ошибок")
    recommendations: List[str] = Field(description="Конкретные рекомендации для улучшения")
    summary: str = Field(description="Общий вывод")
    exam_risk: str = Field(description="low / medium / high — риск провала экзамена")