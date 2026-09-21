"""
Domain Deployment Policies & Four-Eyes Invariants.
"""

from typing import Any
from uuid import UUID


class DeploymentGovernancePolicy:
    """
    Four-Eyes Principle & Gate Validation Invariants.
    """

    @staticmethod
    def validate_four_eyes(model_creator_id: UUID | str, approver_id: UUID | str) -> bool:
        """
        Enforces server-side separation-of-duties: approved_by != created_by.
        """
        return str(model_creator_id) != str(approver_id)

    @staticmethod
    def validate_gate_conditions(gate_metrics: dict[str, Any], thresholds: dict[str, float]) -> dict[str, bool]:
        """
        Validates model performance metrics against pre-registered thresholds.
        """
        results = {}
        for metric, min_val in thresholds.items():
            actual = gate_metrics.get(metric)
            if actual is None:
                results[metric] = False
            else:
                results[metric] = float(actual) >= float(min_val)
        return results
