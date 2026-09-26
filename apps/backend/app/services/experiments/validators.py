from fastapi import HTTPException, status
from app.services.trainers import RegressionTrainer, ClassificationTrainer


class ExperimentValidator:
    """
    Validates algorithm sets and normalizes selection metrics for training experiments (SRS §2.8).
    """

    @staticmethod
    def normalize_selection_metric(
        metric_name: str | None,
        task_type: str,
        direction: str | None = None
    ) -> tuple[str, str]:
        """
        Normalizes selection metric and derives default direction:
        Regression default: rmse (MINIMIZE)
        Classification default: f1_macro (MAXIMIZE)
        """
        if not metric_name:
            if task_type == "REGRESSION":
                return "rmse", "MINIMIZE"
            else:
                return "f1_macro", "MAXIMIZE"

        cleaned = metric_name.lower().replace("-", "_").strip()
        if cleaned in ["macro_f1", "macro-f1", "f1_macro", "f1"]:
            canonical_metric = "f1_macro"
        elif cleaned in ["weighted_f1", "weighted-f1", "f1_weighted"]:
            canonical_metric = "f1_weighted"
        elif cleaned in ["r_2", "r2", "r_squared"]:
            canonical_metric = "r2"
        elif cleaned in ["adjusted_r2", "adj_r2", "adj_r_squared"]:
            canonical_metric = "adjusted_r2"
        elif cleaned in ["roc_auc", "roc-auc", "auc"]:
            canonical_metric = "roc_auc"
        else:
            canonical_metric = cleaned

        if direction:
            canonical_direction = direction.upper().strip()
            if canonical_direction not in ["MAXIMIZE", "MINIMIZE"]:
                canonical_direction = "MINIMIZE" if canonical_metric in ["rmse", "mae", "mse", "log_loss"] else "MAXIMIZE"
        else:
            if canonical_metric in ["rmse", "mae", "mse", "log_loss"]:
                canonical_direction = "MINIMIZE"
            else:
                canonical_direction = "MAXIMIZE"

        return canonical_metric, canonical_direction

    @staticmethod
    def validate_algorithms(task_type: str, algorithms: list[str]) -> list[str]:
        """
        Validates that all requested algorithms belong to the fixed algorithm set
        for the given project task type. Normalizes them to canonical names.
        Raises HTTP 422 on any unknown or mismatched algorithm.
        """
        if not algorithms:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="At least one algorithm must be specified for training."
            )

        canonical_algorithms: list[str] = []
        for alg in algorithms:
            if task_type == "REGRESSION":
                if not RegressionTrainer.is_supported(alg):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Invalid algorithm '{alg}' for task type {task_type}. "
                            f"Allowed algorithms: {', '.join(RegressionTrainer.get_supported_algorithms())}"
                        )
                    )
                canonical_name = RegressionTrainer.to_canonical_name(alg)
            elif task_type == "CLASSIFICATION":
                if not ClassificationTrainer.is_supported(alg):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Invalid algorithm '{alg}' for task type {task_type}. "
                            f"Allowed algorithms: {', '.join(ClassificationTrainer.get_supported_algorithms())}"
                        )
                    )
                canonical_name = ClassificationTrainer.to_canonical_name(alg)
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unsupported project task_type '{task_type}' for model training."
                )

            if canonical_name not in canonical_algorithms:
                canonical_algorithms.append(canonical_name)

        return canonical_algorithms
