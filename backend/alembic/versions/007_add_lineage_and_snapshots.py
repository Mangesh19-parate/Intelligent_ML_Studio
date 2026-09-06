"""add lineage, snapshots, and artifact checksum tracking

Revision ID: 007_add_lineage_and_snapshots
Revises: 006_add_model_training
Create Date: 2026-09-04 20:00:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '007_add_lineage_and_snapshots'
down_revision: Union[str, None] = '006_add_model_training'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create transformation_snapshots table
    op.create_table(
        'transformation_snapshots',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('experiment_id', sa.Uuid(as_uuid=True), sa.ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('config_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_transformation_snapshots_experiment_id'), 'transformation_snapshots', ['experiment_id'], unique=False)

    # 2. Create feature_selection_snapshots table
    op.create_table(
        'feature_selection_snapshots',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('experiment_id', sa.Uuid(as_uuid=True), sa.ForeignKey('experiments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('final_selected_features', sa.JSON(), nullable=False),
        sa.Column('final_selection_method', sa.String(length=30), nullable=False, server_default='rank_aggregation_ensemble'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_feature_selection_snapshots_experiment_id'), 'feature_selection_snapshots', ['experiment_id'], unique=False)

    # 3. Add lineage columns to experiments table
    with op.batch_alter_table('experiments') as batch_op:
        batch_op.add_column(sa.Column('experiment_config', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('dataset_content_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('code_version', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('python_version', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('sklearn_version', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('numpy_version', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('pandas_version', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('model_library_versions', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('environment_capture_method', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('feature_selection_snapshot_id', sa.Uuid(as_uuid=True), nullable=True))
        batch_op.create_foreign_key(
            'fk_experiments_fs_snapshot_id',
            'feature_selection_snapshots',
            ['feature_selection_snapshot_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_check_constraint(
            'chk_experiment_env_capture_method',
            "environment_capture_method IS NULL OR environment_capture_method IN ('CAPTURED_LIVE', 'BACKFILLED_APPROXIMATE')"
        )

    # 4. Add artifact and snapshot link columns to trained_models table
    with op.batch_alter_table('trained_models') as batch_op:
        batch_op.add_column(sa.Column('artifact_path', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('artifact_checksum', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('preprocessing_snapshot_id', sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column('feature_selection_snapshot_id', sa.Uuid(as_uuid=True), nullable=True))
        batch_op.create_foreign_key(
            'fk_trained_models_preprocessing_snapshot_id',
            'transformation_snapshots',
            ['preprocessing_snapshot_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_foreign_key(
            'fk_trained_models_feature_selection_snapshot_id',
            'feature_selection_snapshots',
            ['feature_selection_snapshot_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    op.drop_constraint('fk_trained_models_feature_selection_snapshot_id', 'trained_models', type_='foreignkey')
    op.drop_constraint('fk_trained_models_preprocessing_snapshot_id', 'trained_models', type_='foreignkey')
    op.drop_column('trained_models', 'feature_selection_snapshot_id')
    op.drop_column('trained_models', 'preprocessing_snapshot_id')
    op.drop_column('trained_models', 'artifact_checksum')
    op.drop_column('trained_models', 'artifact_path')

    op.drop_constraint('chk_experiment_env_capture_method', 'experiments', type_='check')
    op.drop_constraint('fk_experiments_fs_snapshot_id', 'experiments', type_='foreignkey')
    op.drop_column('experiments', 'feature_selection_snapshot_id')
    op.drop_column('experiments', 'environment_capture_method')
    op.drop_column('experiments', 'model_library_versions')
    op.drop_column('experiments', 'pandas_version')
    op.drop_column('experiments', 'numpy_version')
    op.drop_column('experiments', 'sklearn_version')
    op.drop_column('experiments', 'python_version')
    op.drop_column('experiments', 'code_version')
    op.drop_column('experiments', 'dataset_content_hash')
    op.drop_column('experiments', 'experiment_config')

    op.drop_index(op.f('ix_feature_selection_snapshots_experiment_id'), table_name='feature_selection_snapshots')
    op.drop_table('feature_selection_snapshots')
    op.drop_index(op.f('ix_transformation_snapshots_experiment_id'), table_name='transformation_snapshots')
    op.drop_table('transformation_snapshots')
