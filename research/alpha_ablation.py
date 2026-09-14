"""
Alpha Ablation & Dataset Condition Evaluation (P2.1, P2.2).
Delegates to authentic nested cross-validation alpha ablation engine.
"""

from research.experiments.run_ablation import (
    run_alpha_ablation_study,
    run_alpha_ablation_for_dataset,
    ALPHA_VALUES as ALPHA_GRID,
    DATASETS,
)


def run_full_ablation():
    summary = run_alpha_ablation_study()
    return summary


if __name__ == "__main__":
    run_full_ablation()
