import csv
from functools import lru_cache
from pathlib import Path

import joblib
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

from style_catalog import FEATURE_COLUMNS, TARGET_COLUMNS, TARGET_FEATURES


BACKEND_DIR = Path(__file__).resolve().parent
DATASET_PATH = BACKEND_DIR / "data" / "style_training_data.csv"
MODEL_PATH = BACKEND_DIR / "models" / "style_recommender.joblib"


def _train_models(dataset):
    models = {}
    for target in TARGET_COLUMNS:
        features = TARGET_FEATURES[target]
        feature_rows = [[row[feature] for feature in features] for row in dataset]
        labels = [row[target] for row in dataset]
        model = make_pipeline(
            OneHotEncoder(handle_unknown="ignore"),
            DecisionTreeClassifier(random_state=42),
        )
        model.fit(feature_rows, labels)
        models[target] = model
    return models


@lru_cache(maxsize=1)
def _load_models():
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_mtime >= DATASET_PATH.stat().st_mtime:
        bundle = joblib.load(MODEL_PATH)
        return bundle["models"], bundle["training_rows"]

    with DATASET_PATH.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if any(column not in reader.fieldnames for column in FEATURE_COLUMNS + TARGET_COLUMNS):
            raise ValueError(f"Training dataset is missing required columns: {DATASET_PATH}")
        dataset = list(reader)
    if not dataset:
        raise ValueError(f"Training dataset is empty or missing required columns: {DATASET_PATH}")

    models = _train_models(dataset)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"models": models, "training_rows": len(dataset)}, MODEL_PATH)
    return models, len(dataset)


def get_recommendations(profile):
    models, _ = _load_models()
    predictions = {
        target: str(models[target].predict([[profile[column] for column in TARGET_FEATURES[target]]])[0])
        for target in TARGET_COLUMNS
    }
    return predictions


def model_status():
    if not DATASET_PATH.exists():
        return {
            "available": False,
            "kind": "synthetic_data_prototype",
            "error": f"Training dataset not found: {DATASET_PATH.name}",
        }

    try:
        _, training_rows = _load_models()
    except (OSError, ValueError, KeyError) as error:
        return {
            "available": False,
            "kind": "synthetic_data_prototype",
            "error": str(error),
        }

    return {
        "available": True,
        "kind": "synthetic_data_prototype",
        "algorithm": "scikit-learn decision trees",
        "training_rows": training_rows,
        "warning": "Generated styling labels are a prototype, not validated real-world ground truth.",
    }
