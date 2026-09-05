"""add deployments, deployment_gates, prediction_logs and experiment threshold flag

Revision ID: 009_add_deployments_and_gates
Revises: 008_add_explainability_summaries
Create Date: 2026-09-05 14:00:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '009_add_deployments_and_gates'
down_revision: Union[str, None] = '008_add_explainability_summaries'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    
    # 1. Retroactive fix: Add deployment_threshold_frozen_at_creation to experiments
    exp_columns = [col['name'] for col in inspector.get_columns('experiments')]
    if 'deployment_threshold_frozen_at_creation' not in exp_columns:
        op.add_column(
            'experiments',
            sa.Column('deployment_threshold_frozen_at_creation', sa.Boolean(), server_default='false', nullable=False)
        )

    # 2. Create deployment_gates table
    tables = inspector.get_table_names()
    if 'deployment_gates' not in tables:
        op.create_table(
            'deployment_gates',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column(
                'model_id',
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey('trained_models.id', ondelete='CASCADE'),
                nullable=False,
                index=True
            ),
            sa.Column('locked_test_evaluated', sa.Boolean(), nullable=False),
            sa.Column('schema_locked', sa.Boolean(), nullable=False),
            sa.Column('artifact_verified', sa.Boolean(), nullable=False),
            sa.Column('lineage_complete', sa.Boolean(), nullable=False),
            sa.Column('performance_threshold_passed', sa.String(length=15), nullable=False),
            sa.Column('user_approved', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('gate_passed', sa.Boolean(), nullable=False),
            sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint(
                "performance_threshold_passed IN ('PASS', 'FAIL', 'UNVERIFIABLE')",
                name='chk_deployment_gate_perf_threshold'
            ),
        )

    # 3. Create deployments table
    if 'deployments' not in tables:
        op.create_table(
            'deployments',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column(
                'model_id',
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey('trained_models.id', ondelete='CASCADE'),
                nullable=False,
                index=True
            ),
            sa.Column('endpoint_path', sa.String(length=200), nullable=False, unique=True),
            sa.Column('status', sa.String(length=20), server_default='LIVE', nullable=False),
            sa.Column(
                'deployed_by',
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey('users.id', ondelete='SET NULL'),
                nullable=True
            ),
            sa.Column('deployed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('log_retention_days', sa.Integer(), server_default='30', nullable=False),
            sa.CheckConstraint(
                "status IN ('LIVE', 'PAUSED', 'RETIRED')",
                name='chk_deployment_status'
            ),
        )

    # 4. Create prediction_logs table
    if 'prediction_logs' not in tables:
        op.create_table(
            'prediction_logs',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column(
                'deployment_id',
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey('deployments.id', ondelete='CASCADE'),
                nullable=False,
                index=True
            ),
            sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column('schema_hash', sa.String(length=64), nullable=False),
            sa.Column('payload_mode', sa.String(length=20), server_default='HASHED', nullable=False),
            sa.Column('input_payload', sa.JSON(), nullable=True),
            sa.Column('prediction_output', sa.JSON(), nullable=True),
            sa.Column('latency_ms', sa.Integer(), nullable=False),
            sa.Column('explanation_requested', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('explanation_latency_ms', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(length=20), server_default='SUCCESS', nullable=False),
            sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
            sa.CheckConstraint(
                "payload_mode IN ('OFF', 'HASHED', 'REDACTED', 'FULL')",
                name='chk_prediction_log_payload_mode'
            ),
            sa.CheckConstraint(
                "status IN ('SUCCESS', 'VALIDATION_ERROR', 'SERVER_ERROR')",
                name='chk_prediction_log_status'
            ),
        )


def downgrade() -> None:
    op.drop_table('prediction_logs')
    op.drop_table('deployments')
    op.drop_table('deployment_gates')
    op.drop_column('experiments', 'deployment_threshold_frozen_at_creation')
