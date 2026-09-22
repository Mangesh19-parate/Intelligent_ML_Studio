"""
ML Training Orchestrator.
Coordinates fold-safe model fitting, cross-validation isolation, and threshold tuning.
"""

from typing import Any
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, StratifiedKFold
from app.services.trainers import (
    RegressionModelTrainer,
    ClassificationModelTrainer,
    BaseModelTrainer,
)
from app.services.evaluation_service import EvaluationService


class TrainingOrchestrator:
    """
    Pure ML Training Engine.
    Executes cross-validation loops with strict outer split isolation.
    """

    def __init__(self, task_type: str = "CLASSIFICATION", random_state: int = 42):
        self.task_type = task_type.upper()
        self.random_state = random_state

    def create_trainer(
        self,
        algorithm_name: str,
        hyperparameters: dict[str, Any] | None = None,
    ) -> BaseModelTrainer:
        if self.task_type == "CLASSIFICATION":
            return ClassificationModelTrainer(
                algorithm_name=algorithm_name,
                hyperparameters=hyperparameters,
                random_state=self.random_state,
            )
        else:
            return RegressionModelTrainer(
                algorithm_name=algorithm_name,
                hyperparameters=hyperparameters,
                random_state=self.random_state,
            )

    def run_cv_evaluation(
        self,
        trainer: BaseModelTrainer,
        X: pd.DataFrame,
        y: pd.Series,
        folds: int = 5,
    ) -> dict[str, Any]:
        """
        Executes leak-free cross-validation over training split.
        """
        if self.task_type == "CLASSIFICATION":
            cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=self.random_state)
        else:
            cv = KFold(n_splits=folds, shuffle=True, random_state=self.random_state)

        fold_scores = []
        oof_preds = np.zeros(len(y)) if self.task_type == "REGRESSION" else np.zeros((len(y), len(np.unique(y))))

        for fold_idx, (train_idx, val_idx) in enumerate(cv.split(X, y)):
            X_tr, y_tr = X.iloc[train_idx], y.iloc[train_idx]
            X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]

            pipeline = trainer.get_pipeline()
            pipeline.fit(X_tr, y_tr)
            preds = pipeline.predict(X_val)
            
            # Record fold performance
            evaluator = EvaluationService()
            if self.task_type == "CLASSIFICATION":
                fold_metric = evaluator.compute_classification_metrics(y_val, preds)
            else:
                fold_metric = evaluator.compute_regression_metrics(y_val, preds)
            fold_scores.append(fold_metric)

        return {
            "folds": fold_scores,
            "mean_score": np.mean([f.get("macro_f1" if self.task_type == "CLASSIFICATION" else "rmse", 0) for f in fold_scores]),
        }
