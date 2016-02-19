# Big Data Smart Socket
# Copyright (C) 2016 Clemson University
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

"""schema

Revision ID: 400d8616184
Revises:
Create Date: 2015-12-18 13:45:44.828587

"""

# revision identifiers, used by Alembic.
revision = '400d8616184'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from app.util import JSONEncodedDict


def upgrade():
    op.create_table('users',
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('name', sa.String(length=100), nullable=False),
                    sa.Column('email', sa.String(length=100), nullable=False),
                    sa.Column('password_hash', sa.String(length=80), nullable=False),
                    sa.Column('is_active', sa.Boolean(), nullable=False),
                    sa.Column('is_admin', sa.Boolean(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False),
                    sa.Column('last_updated_at', sa.DateTime(), nullable=False),
                    sa.PrimaryKeyConstraint('user_id'),
                    sa.UniqueConstraint('email'))

    op.create_table('data_sources',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('label', sa.String(length=100), nullable=False),
                    sa.Column('description', sa.Text(), nullable=True),
                    sa.Column('transfer_mechanism_type', sa.String(length=100), nullable=False),
                    sa.Column('transfer_mechanism_options', JSONEncodedDict(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False),
                    sa.Column('created_by_user_id', sa.Integer(), nullable=False),
                    sa.Column('last_updated_at', sa.DateTime(), nullable=False),
                    sa.Column('last_updated_by_user_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id'], ),
                    sa.ForeignKeyConstraint(['last_updated_by_user_id'], ['users.user_id'], ),
                    sa.PrimaryKeyConstraint('id'))

    op.create_index(op.f('ix_data_sources_label'), 'data_sources', ['label'], unique=True)

    op.create_table('timing_reports',
                    sa.Column('data_source_id', sa.Integer(), nullable=False),
                    sa.Column('report_id', sa.Integer(), autoincrement=False, nullable=False),
                    sa.Column('url', sa.Text(), nullable=False),
                    sa.Column('file_size_bytes', sa.Integer(), nullable=False),
                    sa.Column('transfer_duration_seconds', sa.Float(), nullable=False),
                    sa.Column('file_checksum', sa.String(length=32), nullable=False),
                    sa.Column('mechanism_output', sa.Text(), nullable=True),
                    sa.Column('is_success', sa.Boolean(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False),
                    sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ),
                    sa.PrimaryKeyConstraint('report_id', 'data_source_id'))

    op.create_table('transfer_test_files',
                    sa.Column('data_source_id', sa.Integer(), nullable=False),
                    sa.Column('file_id', sa.Integer(), autoincrement=False, nullable=False),
                    sa.Column('url', sa.Text(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False),
                    sa.Column('created_by_user_id', sa.Integer(), nullable=False),
                    sa.Column('last_updated_at', sa.DateTime(), nullable=False),
                    sa.Column('last_updated_by_user_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id'], ),
                    sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ),
                    sa.ForeignKeyConstraint(['last_updated_by_user_id'], ['users.user_id'], ),
                    sa.PrimaryKeyConstraint('file_id', 'data_source_id'))

    op.create_table('url_matchers',
                    sa.Column('data_source_id', sa.Integer(), nullable=False),
                    sa.Column('matcher_id', sa.Integer(), autoincrement=False, nullable=False),
                    sa.Column('matcher_type', sa.String(length=100), nullable=False),
                    sa.Column('matcher_options', JSONEncodedDict(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False),
                    sa.Column('created_by_user_id', sa.Integer(), nullable=False),
                    sa.Column('last_updated_at', sa.DateTime(), nullable=False),
                    sa.Column('last_updated_by_user_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id'], ),
                    sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ),
                    sa.ForeignKeyConstraint(['last_updated_by_user_id'], ['users.user_id'], ),
                    sa.PrimaryKeyConstraint('matcher_id', 'data_source_id'))

    op.create_table('url_transforms',
                    sa.Column('from_data_source_id', sa.Integer(), nullable=False),
                    sa.Column('transform_id', sa.Integer(), autoincrement=False, nullable=False),
                    sa.Column('to_data_source_id', sa.Integer(), nullable=False),
                    sa.Column('preference_order', sa.Integer(), nullable=False),
                    sa.Column('description', sa.Text(), nullable=True),
                    sa.Column('transform_type', sa.String(length=100), nullable=False),
                    sa.Column('transform_options', JSONEncodedDict(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False),
                    sa.Column('created_by_user_id', sa.Integer(), nullable=False),
                    sa.Column('last_updated_at', sa.DateTime(), nullable=False),
                    sa.Column('last_updated_by_user_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.user_id'], ),
                    sa.ForeignKeyConstraint(['from_data_source_id'], ['data_sources.id'], ),
                    sa.ForeignKeyConstraint(['last_updated_by_user_id'], ['users.user_id'], ),
                    sa.ForeignKeyConstraint(['to_data_source_id'], ['data_sources.id'], ),
                    sa.PrimaryKeyConstraint('transform_id', 'from_data_source_id'))


def downgrade():
    op.drop_table('url_transforms')
    op.drop_table('url_matchers')
    op.drop_table('transfer_test_files')
    op.drop_table('timing_reports')
    op.drop_index(op.f('ix_data_sources_label'), table_name='data_sources')
    op.drop_table('data_sources')
    op.drop_table('users')
