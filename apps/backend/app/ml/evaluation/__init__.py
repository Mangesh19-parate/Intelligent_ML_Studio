"""
ML Evaluation Module.
Multi-metric evaluation suite for regression and classification models (SRS §2.8).
"""

from app.ml.evaluation.metrics import evaluate_regression, evaluate_classification
from app.services.evaluation_service import EvaluationService

__all__ = [
    "evaluate_regression",
    "evaluate_classification",
    "EvaluationService",
]
