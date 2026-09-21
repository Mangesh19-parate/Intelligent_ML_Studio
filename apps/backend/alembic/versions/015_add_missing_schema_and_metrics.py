"""add missing user auth columns, experiment fields, trained model fields, deployment gate approver, and model metrics table

Revision ID: 015_missing_schema
Revises: 014_worker_leases
Create Date: 2026-09-16 14:15:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '015_missing_schema'
down_revision: Union[str, None] = '014_worker_leases'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    dialect_name = bind.dialect.name
    uuid_type = postgresql.UUID(as_uuid=True) if dialect_name == 'postgresql' else sa.Uuid(as_uuid=True)
    json_type = postgresql.JSONB(astext_type=sa.Text()) if dialect_name == 'postgresql' else sa.JSON()

    # 1. Users table columns
    if 'users' in tables:
        cols = {c['name'] for c in inspector.get_columns('users')}
        with op.batch_alter_table('users') as batch_op:
            if 'password_changed_at' not in cols:
                batch_op.add_column(sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True))
            if 'is_two_factor_enabled' not in cols:
                batch_op.add_column(sa.Column('is_two_factor_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')))
            if 'two_factor_secret' not in cols:
                batch_op.add_column(sa.Column('two_factor_secret', sa.String(length=128), nullable=True))
            if 'two_factor_backup_codes' not in cols:
                batch_op.add_column(sa.Column('two_factor_backup_codes', sa.Text(), nullable=True))

    # 2. Experiments table columns
    if 'experiments' in tables:
        cols = {c['name'] for c in inspector.get_columns('experiments')}
        with op.batch_alter_table('experiments') as batch_op:
            if 'selection_metric' not in cols:
                batch_op.add_column(sa.Column('selection_metric', sa.String(length=30), nullable=True))
            if 'selection_direction' not in cols:
                batch_op.add_column(sa.Column('selection_direction', sa.String(length=10), nullable=False, server_default='MAXIMIZE'))
            if 'selected_model_id' not in cols:
                batch_op.add_column(sa.Column('selected_model_id', uuid_type, nullable=True))
                batch_op.create_foreign_key('fk_experiments_selected_model_id', 'trained_models', ['selected_model_id'], ['id'], ondelete='SET NULL')
            if 'locked_test_consumed' not in cols:
                batch_op.add_column(sa.Column('locked_test_consumed', sa.Boolean(), nullable=False, server_default=sa.text('false')))
            if 'locked_test_consumed_at' not in cols:
                batch_op.add_column(sa.Column('locked_test_consumed_at', sa.DateTime(timezone=True), nullable=True))

    # 3. Trained models table columns
    if 'trained_models' in tables:
        cols = {c['name'] for c in inspector.get_columns('trained_models')}
        with op.batch_alter_table('trained_models') as batch_op:
            if 'fit_diagnosis' not in cols:
                batch_op.add_column(sa.Column('fit_diagnosis', sa.String(length=30), nullable=True))
            if 'model_selection_score' not in cols:
                batch_op.add_column(sa.Column('model_selection_score', sa.Numeric(precision=5, scale=2), nullable=True))
            if 'decision_threshold' not in cols:
                batch_op.add_column(sa.Column('decision_threshold', sa.Numeric(precision=6, scale=4), nullable=True, server_default='0.5'))
            if 'created_by' not in cols:
                batch_op.add_column(sa.Column('created_by', uuid_type, nullable=True))
                batch_op.create_foreign_key('fk_trained_models_created_by', 'users', ['created_by'], ['id'], ondelete='SET NULL')

    # 4. Deployment gates table columns
    if 'deployment_gates' in tables:
        cols = {c['name'] for c in inspector.get_columns('deployment_gates')}
        with op.batch_alter_table('deployment_gates') as batch_op:
            if 'approved_by' not in cols:
                batch_op.add_column(sa.Column('approved_by', uuid_type, nullable=True))
                batch_op.create_foreign_key('fk_deployment_gates_approved_by', 'users', ['approved_by'], ['id'], ondelete='SET NULL')

    # 5. Model metrics table
    if 'model_metrics' not in tables:
        op.create_table(
            'model_metrics',
            sa.Column('id', uuid_type, primary_key=True, default=uuid.uuid4),
            sa.Column('model_id', uuid_type, sa.ForeignKey('trained_models.id', ondelete='CASCADE'), nullable=False),
            sa.Column('metric_name', sa.String(length=40), nullable=False),
            sa.Column('split', sa.String(length=30), nullable=False),
            sa.Column('metric_value', sa.Numeric(precision=10, scale=5), nullable=True),
            sa.Column('metric_json', json_type, nullable=True),
            sa.Column('fold_index', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.CheckConstraint("split IN ('TRAIN', 'VALIDATION', 'CV_MEAN', 'LOCKED_TEST', 'TEST_REUSED_DIAGNOSTIC')", name='chk_model_metric_split'),
        )
        op.create_index(op.f('ix_model_metrics_model_id'), 'model_metrics', ['model_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'model_metrics' in tables:
        op.drop_index(op.f('ix_model_metrics_model_id'), table_name='model_metrics')
        op.drop_table('model_metrics')

    if 'deployment_gates' in tables:
        cols = {c['name'] for c in inspector.get_columns('deployment_gates')}
        with op.batch_alter_table('deployment_gates') as batch_op:
            if 'approved_by' in cols:
                batch_op.drop_column('approved_by')

    if 'trained_models' in tables:
        cols = {c['name'] for c in inspector.get_columns('trained_models')}
        with op.batch_alter_table('trained_models') as batch_op:
            if 'created_by' in cols:
                batch_op.drop_column('created_by')
            if 'decision_threshold' in cols:
                batch_op.drop_column('decision_threshold')
            if 'model_selection_score' in cols:
                batch_op.drop_column('model_selection_score')
            if 'fit_diagnosis' in cols:
                batch_op.drop_column('fit_diagnosis')

    if 'experiments' in tables:
        cols = {c['name'] for c in inspector.get_columns('experiments')}
        with op.batch_alter_table('experiments') as batch_op:
            if 'locked_test_consumed_at' in cols:
                batch_op.drop_column('locked_test_consumed_at')
            if 'locked_test_consumed' in cols:
                batch_op.drop_column('locked_test_consumed')
            if 'selected_model_id' in cols:
                batch_op.drop_column('selected_model_id')
            if 'selection_direction' in cols:
                batch_op.drop_column('selection_direction')
            if 'selection_metric' in cols:
                batch_op.drop_column('selection_metric')

    if 'users' in tables:
        cols = {c['name'] for c in inspector.get_columns('users')}
        with op.batch_alter_table('users') as batch_op:
            if 'two_factor_backup_codes' in cols:
                batch_op.drop_column('two_factor_backup_codes')
            if 'two_factor_secret' in cols:
                batch_op.drop_column('two_factor_secret')
            if 'is_two_factor_enabled' in cols:
                batch_op.drop_column('is_two_factor_enabled')
            if 'password_changed_at' in cols:
                batch_op.drop_column('password_changed_at')
