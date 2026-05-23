Я строю Analytics + ML сервис для AI образовательной платформы на хакатоне.

**Контекст:**
Платформа анализирует успеваемость учеников на трёх уровнях: ученик, школа, государство (Министерство образования Узбекистана). Моя часть — собирать данные от AI Grading сервиса, обучить ML модель, генерировать AI рекомендации через Groq, отдавать всё через API на фронт.

**Что уже готово (не моя часть):**
AI Grading сервис :8000, POST /grade возвращает:
`total_score, understanding_level, exam_risk, weak_topics, strong_topics, error_types, recommendations, subject, student_id, assignment_id`

**Моя часть — Analytics сервис :8002**

Kafka consumer: слушаю топик `homework.graded`, сохраняю каждый результат в Postgres.

Postgres схема:
```sql
regions (id, name)
schools (id, region_id, name)
students (id, school_id, name, grade)
submissions (id, student_id, subject, total_score, understanding_level,
             weak_topics jsonb, strong_topics jsonb, error_types jsonb,
             exam_risk, created_at)
predictions (id, student_id, subject, exam_pass_probability, created_at)
regional_stats (id, region_id, subject, avg_score, weak_topics jsonb,
                at_risk_count, trend, month)
recommendations (id, region_id, school_id, level, content jsonb, created_at)
```

ML модель:
- XGBoost или Logistic Regression
- Вход: avg_score_last5, trend, weak_topics_count, submission_rate
- Выход: вероятность сдать экзамен (0-100%)
- Данные: синтетические (500 учеников, 14 регионов, 3 месяца, 4 предмета)
- Паттерны: слабый (45→42→38), средний (65→63→70), сильный (80→85→88)

AI Recommendations через Groq:
```python
async def generate_regional_recommendations(region_stats: dict) -> list[str]:
    # собрать контекст региона
    # вызвать Groq API с промптом
    # вернуть 3 конкретных действия с прогнозом результата
```
Вызывается раз в день по cron. Результат сохраняется в таблицу recommendations.

API endpoints:
```
GET /student/{id}/dashboard     — прогресс, roadmap, prediction
GET /school/{id}/stats          — средний балл, зоны риска, рекомендации
GET /national/stats             — все 14 регионов, тренды, аномалии
GET /national/recommendations   — AI рекомендации для Министерства
GET /alerts                     — аномалии (класс вдруг сдал 95+ за ночь)
```

Anomaly detection (rule-based):
- Весь класс сдал 95+ за одну ночь → флаг
- Регион улучшился на 30%+ за месяц → флаг
- Ученик резко вырос с 30 до 90 за одно ДЗ → флаг

Стек: Python, FastAPI, Postgres, Kafka, scikit-learn/xgboost, Groq API, Docker

Начни с: Postgres схема → синтетические данные → ML модель → API endpoints → Groq recommendations. Экономь токены, сразу пиши код.
