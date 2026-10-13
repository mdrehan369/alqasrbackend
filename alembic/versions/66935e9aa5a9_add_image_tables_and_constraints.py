"""add image tables and constraints

Revision ID: 66935e9aa5a9
Revises: 0797157a47e8
Create Date: 2026-10-11 19:18:57.282198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '66935e9aa5a9'
down_revision: Union[str, Sequence[str], None] = '0797157a47e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'image',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('file_id'),
        sa.UniqueConstraint('file_path'),
    )
    op.create_table(
        'product_image',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('image_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('display_order >= 0', name='ck_product_image_order_nonneg'),
        sa.ForeignKeyConstraint(['image_id'], ['image.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'image_id', name='uq_product_image'),
    )
    op.create_index('ix_product_image_image_id', 'product_image', ['image_id'], unique=False)
    op.create_index('ix_product_image_product_id', 'product_image', ['product_id'], unique=False)
    op.create_index(
        'ux_product_image_primary',
        'product_image',
        ['product_id'],
        unique=True,
        postgresql_where=sa.text('is_primary'),
        sqlite_where=sa.text('is_primary'),
    )

    # category: add missing unique + non-blank constraint
    op.create_unique_constraint('uq_category_name', 'category', ['name'])
    op.create_check_constraint(
        'ck_category_name_not_blank', 'category', 'length(trim(name)) > 0'
    )

    # product: add missing index + non-blank constraint
    op.create_index('ix_product_category_id', 'product', ['category_id'], unique=False)
    op.create_check_constraint(
        'ck_product_title_not_blank', 'product', 'length(trim(title)) > 0'
    )

    # product_variant: rename camelCase columns to snake_case (preserve data)
    op.alter_column(
        'product_variant', 'productType', new_column_name='product_type'
    )
    op.alter_column(
        'product_variant', 'comparePrice', new_column_name='compare_price'
    )
    op.create_index(
        'ix_product_variant_product_id', 'product_variant', ['product_id'], unique=False
    )
    op.create_unique_constraint(
        'uq_product_variant_combo',
        'product_variant',
        ['product_id', 'size', 'unit', 'product_type'],
    )
    op.create_check_constraint(
        'ck_product_variant_size_positive', 'product_variant', 'size > 0'
    )
    op.create_check_constraint(
        'ck_product_variant_price_nonneg', 'product_variant', 'price >= 0'
    )
    op.create_check_constraint(
        'ck_product_variant_compare_price_nonneg', 'product_variant', 'compare_price >= 0'
    )
    op.create_check_constraint(
        'ck_product_variant_compare_price_gte_price',
        'product_variant',
        'compare_price >= price',
    )
    op.create_check_constraint(
        'ck_product_variant_stock_nonneg', 'product_variant', 'stock >= 0'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # product_variant: drop constraints then rename columns back
    op.drop_constraint('ck_product_variant_stock_nonneg', 'product_variant', type_='check')
    op.drop_constraint(
        'ck_product_variant_compare_price_gte_price', 'product_variant', type_='check'
    )
    op.drop_constraint(
        'ck_product_variant_compare_price_nonneg', 'product_variant', type_='check'
    )
    op.drop_constraint(
        'ck_product_variant_price_nonneg', 'product_variant', type_='check'
    )
    op.drop_constraint(
        'ck_product_variant_size_positive', 'product_variant', type_='check'
    )
    op.drop_constraint('uq_product_variant_combo', 'product_variant', type_='unique')
    op.drop_index('ix_product_variant_product_id', table_name='product_variant')
    op.alter_column(
        'product_variant', 'compare_price', new_column_name='comparePrice'
    )
    op.alter_column(
        'product_variant', 'product_type', new_column_name='productType'
    )

    # product
    op.drop_constraint('ck_product_title_not_blank', 'product', type_='check')
    op.drop_index('ix_product_category_id', table_name='product')

    # category
    op.drop_constraint('ck_category_name_not_blank', 'category', type_='check')
    op.drop_constraint('uq_category_name', 'category', type_='unique')

    # image tables
    op.drop_index(
        'ux_product_image_primary',
        table_name='product_image',
        postgresql_where=sa.text('is_primary'),
        sqlite_where=sa.text('is_primary'),
    )
    op.drop_index('ix_product_image_product_id', table_name='product_image')
    op.drop_index('ix_product_image_image_id', table_name='product_image')
    op.drop_table('product_image')
    op.drop_table('image')
