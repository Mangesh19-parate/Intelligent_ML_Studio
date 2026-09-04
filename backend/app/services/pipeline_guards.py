from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.dataset import Dataset
from app.models.dataset_split import DatasetSplit

def require_split_exists(db: Session, project_id: UUID | str) -> None:
    """
    Guard function for Day 3+ services.
    Enforces that an outer split (Development / Locked Test partition) has been established
    for the project's active dataset before allowing any profiling, transformation,
    feature engineering, or model training.
    """
    if isinstance(project_id, str):
        try:
            project_id = UUID(project_id)
        except Exception:
            pass

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Fetch latest dataset version
    latest_dataset = (
        db.query(Dataset)
        .filter(Dataset.project_id == project_id)
        .order_by(Dataset.version_number.desc())
        .first()
    )

    if not latest_dataset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no uploaded datasets."
        )

    # Check for active DEVELOPMENT split
    split_exists = (
        db.query(DatasetSplit)
        .filter(
            DatasetSplit.dataset_id == latest_dataset.id,
            DatasetSplit.split_type == "DEVELOPMENT"
        )
        .first()
        is not None
    )

    if not split_exists:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project pipeline requires an established outer split. Please create a train/test split on the active dataset before proceeding."
        )
