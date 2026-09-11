"""
Counterfactual Experiment Diff Service (Week 12 Feature per PRD & SRS).

Computes structured comparative diffs between two experiments to isolate:
1. Preprocessing and transformation differences
2. Selected feature differences (added / removed / retained)
3. Model algorithm & hyperparameter configuration differences
4. Validation & test metric performance deltas (cross-validation score, locked test score)
5. Lineage & environment variations (dataset hash, python/library versions)
"""

import uuid
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.experiment import Experiment
from app.models.trained_model import TrainedModel
from app.models.model_metric import ModelMetric



class ExperimentDiffService:
    """
    Computes counterfactual 'what changed' comparisons between two experiments.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_experiment_or_404(self, experiment_id: Any) -> Experiment:
        if isinstance(experiment_id, str):
            try:
                exp_uuid = uuid.UUID(experiment_id)
            except ValueError:
                raise HTTPException(status_code=404, detail=f"Invalid experiment UUID: {experiment_id}")
        else:
            exp_uuid = experiment_id

        exp = self.db.query(Experiment).filter(Experiment.id == exp_uuid).first()
        if not exp:
            raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
        return exp

    def compute_diff(self, experiment_a_id: Any, experiment_b_id: Any) -> dict[str, Any]:
        """
        Computes the complete structured diff: Experiment B compared against baseline Experiment A.
        """
        exp_a = self.get_experiment_or_404(experiment_a_id)
        exp_b = self.get_experiment_or_404(experiment_b_id)

        config_a = exp_a.experiment_config or {}
        config_b = exp_b.experiment_config or {}

        # 1. Pipeline configuration comparison
        pipeline_diff = {
            "task_type": {
                "experiment_a": exp_a.task_type,
                "experiment_b": exp_b.task_type,
                "changed": exp_a.task_type != exp_b.task_type,
            },
            "fold_count": {
                "experiment_a": exp_a.fold_count,
                "experiment_b": exp_b.fold_count,
                "changed": exp_a.fold_count != exp_b.fold_count,
            },
            "cv_seed": {
                "experiment_a": exp_a.cv_seed,
                "experiment_b": exp_b.cv_seed,
                "changed": exp_a.cv_seed != exp_b.cv_seed,
            },
            "selection_metric": {
                "experiment_a": exp_a.selection_metric,
                "experiment_b": exp_b.selection_metric,
                "changed": exp_a.selection_metric != exp_b.selection_metric,
            },
        }

        # 2. Feature selection difference
        feats_a = set(config_a.get("selected_features", []))
        feats_b = set(config_b.get("selected_features", []))
        added_features = sorted(list(feats_b - feats_a))
        removed_features = sorted(list(feats_a - feats_b))
        common_features = sorted(list(feats_a.intersection(feats_b)))

        feature_diff = {
            "features_in_a_count": len(feats_a),
            "features_in_b_count": len(feats_b),
            "added_in_b": added_features,
            "removed_in_b": removed_features,
            "retained_common_count": len(common_features),
            "feature_set_changed": bool(added_features or removed_features),
        }

        # 3. Model Algorithm & Hyperparameters diff
        models_a = {m.get("algorithm"): m for m in config_a.get("models", []) if isinstance(m, dict)}
        models_b = {m.get("algorithm"): m for m in config_b.get("models", []) if isinstance(m, dict)}
        all_algos = sorted(list(set(models_a.keys()).union(set(models_b.keys()))))

        algo_diffs = {}
        for algo in all_algos:
            m_a = models_a.get(algo)
            m_b = models_b.get(algo)
            if m_a and not m_b:
                algo_diffs[algo] = {"status": "REMOVED_IN_B", "config_a": m_a}
            elif not m_a and m_b:
                algo_diffs[algo] = {"status": "ADDED_IN_B", "config_b": m_b}
            else:
                params_a = m_a.get("hyperparameters", {})
                params_b = m_b.get("hyperparameters", {})
                algo_diffs[algo] = {
                    "status": "COMMON",
                    "hyperparameters_changed": params_a != params_b,
                    "params_a": params_a,
                    "params_b": params_b,
                }

        # 4. Performance Metric Deltas (CV & Test Metrics)
        metrics_a = self._fetch_experiment_metrics(exp_a.id)
        metrics_b = self._fetch_experiment_metrics(exp_b.id)

        all_metric_names = sorted(list(set(metrics_a.keys()).union(set(metrics_b.keys()))))
        metric_deltas = {}
        for m_name in all_metric_names:
            val_a = metrics_a.get(m_name)
            val_b = metrics_b.get(m_name)
            if val_a is not None and val_b is not None:
                delta = round(val_b - val_a, 6)
                pct_change = round((delta / abs(val_a) * 100.0), 2) if val_a != 0 else 0.0
                metric_deltas[m_name] = {
                    "experiment_a_value": val_a,
                    "experiment_b_value": val_b,
                    "delta": delta,
                    "pct_change": pct_change,
                    "improved": delta > 0 if "rmse" not in m_name.lower() else delta < 0,
                }
            else:
                metric_deltas[m_name] = {
                    "experiment_a_value": val_a,
                    "experiment_b_value": val_b,
                    "delta": None,
                    "pct_change": None,
                }

        # 5. Lineage & Environment Check
        lineage_diff = {
            "dataset_content_hash": {
                "experiment_a": exp_a.dataset_content_hash,
                "experiment_b": exp_b.dataset_content_hash,
                "same_dataset": exp_a.dataset_content_hash == exp_b.dataset_content_hash,
            },
            "code_version": {
                "experiment_a": exp_a.code_version,
                "experiment_b": exp_b.code_version,
                "same_code_version": exp_a.code_version == exp_b.code_version,
            },
            "python_version": {
                "experiment_a": exp_a.python_version,
                "experiment_b": exp_b.python_version,
            },
        }

        return {
            "experiment_a_id": str(exp_a.id),
            "experiment_b_id": str(exp_b.id),
            "pipeline_diff": pipeline_diff,
            "feature_selection_diff": feature_diff,
            "model_algorithm_diff": algo_diffs,
            "metric_deltas": metric_deltas,
            "lineage_diff": lineage_diff,
            "summary": self._generate_diff_summary(feature_diff, algo_diffs, metric_deltas),
        }

    def _fetch_experiment_metrics(self, experiment_id: uuid.UUID) -> dict[str, float]:
        """Collects latest evaluation metric values for the experiment."""
        models = self.db.query(TrainedModel).filter(TrainedModel.experiment_id == experiment_id).all()
        res = {}
        for m in models:
            eval_metrics = self.db.query(ModelMetric).filter(ModelMetric.model_id == m.id).all()
            for em in eval_metrics:
                key = f"{m.algorithm_name}_{em.metric_name}"
                if em.metric_value is not None:
                    res[key] = round(float(em.metric_value), 6)
        return res



    def _generate_diff_summary(
        self,
        feat_diff: dict[str, Any],
        algo_diff: dict[str, Any],
        metric_deltas: dict[str, Any],
    ) -> str:
        changes = []
        if feat_diff["feature_set_changed"]:
            added = len(feat_diff["added_in_b"])
            removed = len(feat_diff["removed_in_b"])
            changes.append(f"Features: +{added} added, -{removed} removed")
        else:
            changes.append("Features: Identical feature subset")

        changed_algos = [k for k, v in algo_diff.items() if v.get("status") != "COMMON" or v.get("hyperparameters_changed")]
        if changed_algos:
            changes.append(f"Models: Changes in {', '.join(changed_algos)}")
        else:
            changes.append("Models: Identical model configurations")

        return "; ".join(changes)
