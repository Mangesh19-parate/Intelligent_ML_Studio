"""
Experiment Subsystem Domain Modules (SRS §2.8 - §2.12).
Modular domain decomposition of validation, artifact management, evaluation, and training orchestration.
"""

from app.services.experiments.validators import ExperimentValidator
from app.services.experiments.artifact_manager import (
    ExperimentArtifactManager,
    ORPHANED_RECOVERABLE_REGISTRY,
    get_orphaned_recoverable_registry,
    clear_orphaned_recoverable_registry,
)
from app.services.experiments.evaluator import ExperimentEvaluator
from app.services.experiments.model_trainer import ModelTrainer
from app.services.experiments.passport_signer import ModelPassportSigner

__all__ = [
    "ExperimentValidator",
    "ExperimentArtifactManager",
    "ExperimentEvaluator",
    "ModelTrainer",
    "ModelPassportSigner",
    "ORPHANED_RECOVERABLE_REGISTRY",
    "get_orphaned_recoverable_registry",
    "clear_orphaned_recoverable_registry",
]
