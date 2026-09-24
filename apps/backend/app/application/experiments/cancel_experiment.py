"""
Application Use Case: Cancel Experiment.
Gracefully transitions running or queued experiment tasks to CANCELLED state.
"""

from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.repositories.experiment_repository import ExperimentRepository
from app.models.durable_task import DurableTask
from app.tasks.task_state import TaskState


from app.config.state_machines import ExperimentState

def cancel_experiment_use_case(
    db: Session,
    experiment_id: UUID | str,
) -> dict[str, str]:
    """
    Cancels an active or queued experiment and aborts its durable task.
    Enforces clean state machine separation:
    - ExperimentState -> TRAINING_FAILED
    - TaskState -> CANCELLED
    """
    exp_repo = ExperimentRepository(db)
    exp = exp_repo.get_by_id(experiment_id)
    if not exp:
        raise ValueError(f"Experiment '{experiment_id}' not found.")

    exp_repo.update_status(exp.id, ExperimentState.TRAINING_FAILED.value, completed_at=datetime.now(timezone.utc))

    # Cancel active tasks
    tasks = db.query(DurableTask).filter(
        DurableTask.experiment_id == exp.id,
        DurableTask.state.in_([TaskState.QUEUED.value, TaskState.RUNNING.value])
    ).all()
    
    for t in tasks:
        t.state = TaskState.CANCELLED.value
        t.completed_at = datetime.now(timezone.utc)
        t.error_message = "Experiment cancelled by user."
        db.add(t)
    db.commit()

    return {
        "experiment_id": str(exp.id),
        "status": ExperimentState.TRAINING_FAILED.value,
    }
