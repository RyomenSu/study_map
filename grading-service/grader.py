import json
import os
import urllib.request
import urllib.error

import google.generativeai as genai
from models import GradingResult, ProblemResult, UnderstandingLevel, ErrorType

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))


def _max_input_chars() -> int:
    raw = os.getenv("GRADING_MAX_INPUT_CHARS", "4000").strip()
    try:
        value = int(raw)
        return value if value > 0 else 4000
    except ValueError:
        return 4000


def _model_candidates() -> list[str]:
    configured = os.getenv("GEMINI_MODEL", "").strip()
    if configured:
        return [configured]
    # Fallback order for compatibility across different Gemini API accounts.
    return [
        "gemini-2.0-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
    ]


def _is_ollama_fallback_enabled() -> bool:
    return os.getenv("GRADING_OLLAMA_FALLBACK", "true").strip().lower() in {"1", "true", "yes", "on"}


def _ollama_url() -> str:
    return os.getenv("OLLAMA_URL", "http://host.docker.internal:11434/api/generate")


def _ollama_model() -> str:
    return os.getenv("GRADING_OLLAMA_MODEL", "mistral:7b")


def _extract_json_text(raw: str) -> str:
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start:end + 1]
    return cleaned


def _grade_with_ollama(prompt: str) -> str:
    payload = {
        "model": _ollama_model(),
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1}
    }
    req = urllib.request.Request(
        _ollama_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        body = resp.read().decode("utf-8")
        parsed = json.loads(body)
        return str(parsed.get("response", "")).strip()

SYSTEM_PROMPT = """Ты — опытный учитель и образовательный аналитик.
Тебе дают домашнюю работу ученика по любому школьному предмету.

Твоя задача:
1. Определить все задачи и ответы в тексте
2. Оценить каждую задачу по 100-балльной шкале с учётом специфики предмета
3. Выявить сильные и слабые темы
4. Определить типы ошибок
5. Дать конкретные рекомендации для улучшения
6. Оценить риск провала экзамена

Правила оценки:
- 90-100: полностью правильно
- 70-89: правильный подход, мелкие ошибки  
- 50-69: частично правильно
- 30-49: неправильный подход, но есть понимание
- 0-29: неверно или не решено

Уровень понимания:
- отличный: 90-100
- хороший: 75-89
- средний: 55-74
- слабый: 35-54
- критический: 0-34

Риск экзамена:
- low: total_score >= 75
- medium: total_score 50-74
- high: total_score < 50

Типы ошибок (используй только из списка):
концептуальные, вычислительные, логические, фактические, неполные ответы, языковые/грамматические

Отвечай ТОЛЬКО валидным JSON без markdown:
{
  "total_score": <целое число 0-100>,
  "understanding_level": "<отличный|хороший|средний|слабый|критический>",
  "summary": "<общий вывод на русском>",
  "exam_risk": "<low|medium|high>",
  "weak_topics": ["<тема>"],
  "strong_topics": ["<тема>"],
  "error_types": ["<тип ошибки>"],
  "recommendations": ["<конкретная рекомендация>"],
  "problems": [
    {
      "problem_number": 1,
      "problem_text": "<текст задачи>",
      "student_answer": "<ответ студента>",
      "score": <0-100>,
      "feedback": "<подробный фидбек на русском>",
      "correct": <true/false>,
      "topics": ["<тема задачи>"],
      "error_types": ["<тип ошибки если есть>"]
    }
  ]
}"""


async def grade_submission(extracted_text: str, subject: str) -> GradingResult:
    clipped_text = extracted_text[:_max_input_chars()]
    prompt = f"{SYSTEM_PROMPT}\n\nПредмет: {subject}\n\nДомашняя работа:\n{clipped_text}"

    last_error = None
    raw = ""
    for model_name in _model_candidates():
        try:
            print(f"[GRADER] Trying Gemini model: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = await model.generate_content_async(prompt)
            raw = response.text.strip()
            print(f"[GRADER] Gemini model succeeded: {model_name}")
            break
        except Exception as e:
            last_error = e
            print(f"[GRADER] Gemini model failed: {model_name} -> {e}")

    if not raw:
        if _is_ollama_fallback_enabled():
            print(f"[GRADER] Gemini unavailable. Falling back to Ollama model: {_ollama_model()}")
            raw = _grade_with_ollama(prompt)
        if not raw:
            raise RuntimeError(f"No working grading model found. Last error: {last_error}")

    raw = _extract_json_text(raw)

    parsed = json.loads(raw)

    problems = []
    for p in parsed["problems"]:
        problems.append(ProblemResult(
            problem_number=p["problem_number"],
            problem_text=p["problem_text"],
            student_answer=p["student_answer"],
            score=p["score"],
            feedback=p["feedback"],
            correct=p["correct"],
            topics=p.get("topics", []),
            error_types=[ErrorType(e) for e in p.get("error_types", []) if e in ErrorType._value2member_map_],
        ))

    return GradingResult(
        student_id=None,
        assignment_id=None,
        subject=subject,
        total_score=parsed["total_score"],
        understanding_level=UnderstandingLevel(parsed["understanding_level"]),
        problems=problems,
        weak_topics=parsed.get("weak_topics", []),
        strong_topics=parsed.get("strong_topics", []),
        error_types=[ErrorType(e) for e in parsed.get("error_types", []) if e in ErrorType._value2member_map_],
        recommendations=parsed.get("recommendations", []),
        summary=parsed["summary"],
        exam_risk=parsed["exam_risk"],
    )