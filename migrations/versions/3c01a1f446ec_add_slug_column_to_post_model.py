"""Add slug column to Post model

Revision ID: 3c01a1f446ec
Revises: a82fc192473f
Create Date: 2025-04-02 02:26:28.109955

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3c01a1f446ec'
down_revision = 'a82fc192473f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('slug', sa.String(length=150), nullable=False))
        batch_op.create_index(batch_op.f('ix_post_slug'), ['slug'], unique=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('post', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_post_slug'))
        batch_op.drop_column('slug')

    # ### end Alembic commands ###
