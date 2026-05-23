"""
ML model: XGBoost predicting exam pass probability (0-100%).
Features: avg_score_last5, trend, weak_topics_count, submission_rate
"""
import numpy as np
import joblib
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
import asyncpg
from typing import Optional

MODEL_PATH = Path("model.joblib")


def build_training_data():
    """Generate synthetic training set matching our 3-pattern schema."""
    rng = np.random.default_rng(42)
    X, y = [], []

    patterns = {
        "weak":   {"avg": (35, 50), "trend": (-5, 0),  "weak": (3, 6), "rate": (0.4, 0.7)},
        "medium": {"avg": (55, 72), "trend": (-2, 5),  "weak": (1, 4), "rate": (0.6, 0.9)},
        "strong": {"avg": (75, 95), "trend": (1, 8),   "weak": (0, 2), "rate": (0.8, 1.0)},
    }
    labels = {"weak": 0, "medium": 1, "strong": 1}  # pass threshold ~55

    for pattern, cfg in patterns.items():
        n = 500
        avg = rng.uniform(*cfg["avg"], n)
        trend = rng.uniform(*cfg["trend"], n)
        weak = rng.integers(*cfg["weak"], n)
        rate = rng.uniform(*cfg["rate"], n)
        noise = rng.normal(0, 0.05, n)
        X.extend(np.column_stack([avg, trend, weak, rate + noise]))
        base_label = labels[pattern]
        # Add some noise to labels
        flipped = rng.random(n) < 0.08
        y.extend(np.where(flipped, 1 - base_label, base_label))

    return np.array(X), np.array(y)


def train_model():
    X, y = build_training_data()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = XGBClassifier(
        n_estimators=100, max_depth=4, learning_rate=0.1,
        use_label_encoder=False, eval_metric="logloss", random_state=42
    )
    model.fit(X_train, y_train)
    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    print(f"Model AUC: {auc:.3f}")
    joblib.dump(model, MODEL_PATH)
    return model


def load_model():
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return train_model()


_model = None

def get_model():
    global _model
    if _model is None:
        _model = load_model()
    return _model


async def compute_student_features(pool: asyncpg.Pool, student_id: str, subject: str) -> Optional[dict]:
    """Compute features from the main app's grades table."""
    from datetime import datetime, timedelta
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT g.score / g.max_score * 100 AS pct, g.graded_at
            FROM grades g
            JOIN submissions s ON s.id = g.submission_id
            JOIN assignments a ON a.id = s.assignment_id
            JOIN courses c ON c.id = a.course_id
            WHERE s.student_id = $1::uuid AND c.name = $2
            ORDER BY g.graded_at DESC LIMIT 5
        """, student_id, subject)

    if not rows:
        return None

    scores = [float(r["pct"]) for r in rows]
    avg_score = np.mean(scores)
    trend = scores[0] - scores[-1] if len(scores) > 1 else 0
    weak_count = sum(1 for s in scores if s < 60)

    cutoff = datetime.now() - timedelta(days=30)
    recent = sum(1 for r in rows if r["graded_at"] >= cutoff)
    submission_rate = min(recent / 8, 1.0)

    return {
        "avg_score_last5": avg_score,
        "trend": trend,
        "weak_topics_count": float(weak_count),
        "submission_rate": submission_rate,
    }


def predict_pass_probability(features: dict) -> float:
    model = get_model()
    X = np.array([[
        features["avg_score_last5"],
        features["trend"],
        features["weak_topics_count"],
        features["submission_rate"],
    ]])
    prob = model.predict_proba(X)[0][1]
    return round(float(prob) * 100, 1)


if __name__ == "__main__":
    train_model()
    print("Model trained and saved.")