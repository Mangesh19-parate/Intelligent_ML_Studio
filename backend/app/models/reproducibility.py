import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, func, Uuid
from sqlalchemy.orm import relationship

from app.core.database import Base


class ReproducibilityRun(Base):
    """
    ReproducibilityRun model for tracking independent deterministic replay runs.
    Enforces that:
    1. Replay is executed solely on CV partition without accessing Locked Test.
    2. Exact metric differences and tolerances are recorded.
    3. Dataset and pipeline config hashes match source experiment.
    """
    __tablename__ = "reproducibility_runs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_experiment_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status = Column(String(30), nullable=False)  # MATCHED, MISMATCHED, FAILED
    expected_metric = Column(Float, nullable=True)
    observed_metric = Column(Float, nullable=True)
    difference = Column(Float, nullable=True)
    absolute_tolerance = Column(Float, nullable=False, default=0.001)
    relative_tolerance = Column(Float, nullable=False, default=0.01)
    code_version = Column(String(100), nullable=True)
    dataset_hash = Column(String(64), nullable=True)
    config_hash = Column(String(64), nullable=True)
    locked_test_accessed = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    source_experiment = relationship("Experiment", backref="reproducibility_runs")
