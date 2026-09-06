"""add explainability_summaries table

Revision ID: 008_add_explainability_summaries
Revises: 007_add_lineage_and_snapshots
Create Date: 2026-09-04 20:30:00.000000

"""
from typing import Sequence, Union
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008_add_explainability_summaries'
down_revision: Union[str, None] = '007_add_lineage_and_snapshots'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'explainability_summaries',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            'model_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('trained_models.id', ondelete='CASCADE'),
            nullable=False,
            unique=True
        ),
        sa.Column('shap_values', sa.JSON(), nullable=False),
        sa.Column('background_sample_size', sa.Integer(), nullable=False),
        sa.Column('explainer_type', sa.String(length=20), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "explainer_type IN ('TREE', 'LINEAR', 'KERNEL')",
            name='chk_explainability_summary_explainer_type'
        ),
    )
    op.create_index(op.f('ix_explainability_summaries_model_id'), 'explainability_summaries', ['model_id'], unique=True)


def downgrade() -> None:
    op.drop_constraint('chk_explainability_summary_explainer_type', 'explainability_summaries', type_='check')
    op.drop_index(op.f('ix_explainability_summaries_model_id'), table_name='explainability_summaries')
    op.drop_table('explainability_summaries')
