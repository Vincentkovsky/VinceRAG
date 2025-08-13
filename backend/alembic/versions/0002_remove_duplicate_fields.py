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
    # Check if columns exist before trying to migrate them
    connection = op.get_bind()
    
    # Check if size and url columns exist
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'documents' 
        AND column_name IN ('size', 'url')
    """))
    existing_columns = [row[0] for row in result]
    
    # Only migrate data if the columns exist
    if existing_columns:
        # Update existing records to move size and url to metadata
        migration_parts = []
        if 'size' in existing_columns:
            migration_parts.append("CASE WHEN size IS NOT NULL THEN jsonb_build_object('fileSize', size) ELSE '{}'::jsonb END")
        if 'url' in existing_columns:
            migration_parts.append("CASE WHEN url IS NOT NULL THEN jsonb_build_object('url', url) ELSE '{}'::jsonb END")
        
        if migration_parts:
            migration_sql = f"""
                UPDATE documents 
                SET metadata = COALESCE(metadata, '{{}}')::jsonb || {' || '.join(migration_parts)}
                WHERE {' OR '.join([f'{col} IS NOT NULL' for col in existing_columns])}
            """
            connection.execute(sa.text(migration_sql))
    
        # Drop the columns if they exist
        if 'size' in existing_columns:
            op.drop_column('documents', 'size')
        if 'url' in existing_columns:
            op.drop_column('documents', 'url')
    
    # Make metadata column NOT NULL with default empty object if it's not already
    try:
        op.alter_column('documents', 'metadata',
                       existing_type=sa.JSON(),
                       nullable=False,
                       server_default=sa.text("'{}'::json"))
    except Exception:
        # Column might already be configured correctly
        pass


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