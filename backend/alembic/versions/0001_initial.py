"""initial schema

Revision ID: 0001
Create Date: 2026-01-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None


def upgrade():
    # On Postgres, after create_all run:
    #   SELECT create_hypertable('candles','ts', chunk_time_interval => INTERVAL '7 days');
    # Tables are created from app.db.models metadata in env.py; this migration
    # is the place to add the hypertable + JSONB/GIN indexes for prod.
    op.execute("-- see docs/DATABASE_SCHEMA.sql for full DDL")


def downgrade():
    pass
