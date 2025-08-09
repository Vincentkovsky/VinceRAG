"""Remove duplicate fields from documents table

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, migrate existing data from size and url columns to metadata
    # This is a data migration step
    
    # Get connection
    connection = op.get_bind()
    
    # Update existing records to move size and url to metadata
    connection.execute(sa.text("""
        UPDATE documents 
        SET metadata = COALESCE(metadata, '{}')::jsonb || 
                      CASE 
                        WHEN size IS NOT NULL THEN jsonb_build_object('fileSize', size)
                        ELSE '{}'::jsonb
                      END ||
                      CASE 
                        WHEN url IS NOT NULL THEN jsonb_build_object('url', url)
                        ELSE '{}'::jsonb
                      END
        WHERE size IS NOT NULL OR url IS NOT NULL
    """))
    
    # Now drop the redundant columns
    op.drop_column('documents', 'size')
    op.drop_column('documents', 'url')
    
    # Make metadata column NOT NULL with default empty object
    op.alter_column('documents', 'metadata',
                   existing_type=sa.JSON(),
                   nullable=False,
                   server_default=sa.text("'{}'::json"))


def downgrade() -> None:
    # Add back the columns
    op.add_column('documents', sa.Column('size', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('url', sa.Text(), nullable=True))
    
    # Make metadata nullable again
    op.alter_column('documents', 'metadata',
                   existing_type=sa.JSON(),
                   nullable=True,
                   server_default=None)
    
    # Migrate data back from metadata to columns
    connection = op.get_bind()
    
    # Move fileSize from metadata to size column
    connection.execute(sa.text("""
        UPDATE documents 
        SET size = (metadata->>'fileSize')::integer
        WHERE metadata ? 'fileSize'
    """))
    
    # Move url from metadata to url column
    connection.execute(sa.text("""
        UPDATE documents 
        SET url = metadata->>'url'
        WHERE metadata ? 'url'
    """))