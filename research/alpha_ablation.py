"""
Alpha Ablation & Dataset Condition Evaluation (P2.1, P2.2).
Evaluates the Pareto trade-off across stability weighting alphas [0.00, 0.25, 0.50, 0.70, 0.85, 1.00]
and characterizes the exact dataset conditions (dimensionality, correlation, sample/feature ratio)
under which stability aggregation outperforms baseline selection.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import f1_score, root_mean_squared_error
from sklearn.model_selection import StratifiedKFold, KFold

from research.dataset_loader import load_dataset
from research.outer_split import create_split
from research.feature_selectors import rank_aggregation_ensemble, _resolve_k
from research.stability import StabilityScorer


ALPHA_GRID = [0.00, 0.25, 0.50, 0.70, 0.85, 1.00]
DATASETS = ["breast_cancer", "adult_income", "california_housing", "bike_sharing"]


def run_alpha_ablation_for_dataset(dataset_name: str, seed: int = 42) -> list[dict]:
    """Runs cross-validation across alpha grid on the Development partition."""
    X, y, task_type = load_dataset(dataset_name)
    split = create_split(X, y, task_type, seed=seed)
    X_dev = X.iloc[split.dev_indices].reset_index(drop=True)
    y_dev = y.iloc[split.dev_indices].reset_index(drop=True)

    feature_names = list(X_dev.columns)
    p = len(feature_names)
    k = _resolve_k(0.5, p)

    # 1. Pre-estimate stability vector strictly on Development slice
    stab_vec, _ = StabilityScorer.estimate_stability_on_development(
        X_dev, y_dev, task_type, n_splits=5, n_repeats=2, seed=seed, k_features=0.5
    )

    results = []
    is_clf = task_type.upper() == "CLASSIFICATION"

    for alpha in ALPHA_GRID:
        scorer = StabilityScorer(alpha=alpha)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed) if is_clf else KFold(n_splits=5, shuffle=True, random_state=seed)
        splits = cv.split(X_dev, y_dev) if is_clf else cv.split(X_dev)

        fold_scores = []
        selected_features_per_fold = []

        for fold_idx, (tr_idx, val_idx) in enumerate(splits):
            X_tr, y_tr = X_dev.iloc[tr_idx], y_dev.iloc[tr_idx]
            X_val, y_val = X_dev.iloc[val_idx], y_dev.iloc[val_idx]

            # Importance scores on training slice
            _, _, rank_scores = rank_aggregation_ensemble(X_tr, y_tr, task_type, seed=seed + fold_idx)
            
            # Combine importance and stability with alpha weight
            final_scores = scorer.compute_final_score(rank_scores, stab_vec)
            sorted_idx = np.argsort(-final_scores, kind="stable")
            top_k_indices = sorted_idx[:k]
            top_k_names = [feature_names[i] for i in top_k_indices]
            selected_features_per_fold.append(top_k_names)

            # Fit reference model on selected features
            if is_clf:
                clf = RandomForestClassifier(n_estimators=50, random_state=seed, max_depth=8)
                clf.fit(X_tr[top_k_names], y_tr)
                preds = clf.predict(X_val[top_k_names])
                score = f1_score(y_val, preds, average="macro")
            else:
                reg = RandomForestRegressor(n_estimators=50, random_state=seed, max_depth=8)
                reg.fit(X_tr[top_k_names], y_tr)
                preds = reg.predict(X_val[top_k_names])
                score = root_mean_squared_error(y_val, preds)

            fold_scores.append(score)

        # Compute empirical selection stability across folds for this alpha
        stab_dict = StabilityScorer.compute_stability_from_subsets(selected_features_per_fold, feature_names)
        mean_stab = float(np.mean([stab_dict[f] for f in feature_names if stab_dict[f] > 0]))

        results.append({
            "dataset": dataset_name,
            "task_type": task_type,
            "alpha": alpha,
            "mean_cv_score": float(np.mean(fold_scores)),
            "std_cv_score": float(np.std(fold_scores)),
            "mean_stability": mean_stab,
            "k_selected": k,
            "total_features": p,
        })

    return results


def run_full_ablation():
    all_results = []
    for d in DATASETS:
        print(f"Running alpha ablation for {d}...")
        res = run_alpha_ablation_for_dataset(d)
        all_results.extend(res)

    df = pd.DataFrame(all_results)
    out_path = Path(__file__).resolve().parent / "results" / "alpha_ablation.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path)
    print(f"Saved ablation results to {out_path}")
    print(df.to_string())
    return df


if __name__ == "__main__":
    run_full_ablation()
