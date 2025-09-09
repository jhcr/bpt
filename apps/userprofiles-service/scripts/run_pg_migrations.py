#!/usr/bin/env python3
"""
PostgreSQL migration runner for UserProfiles service

Runs migrations in order: init → tables → sql → functions → procedures
Only tracks versioned SQL files (in sql/ directory) in migration registry.
"""

import os
import glob
import psycopg
from pathlib import Path
import structlog

# Setup basic logging
structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger
)

logger = structlog.get_logger(__name__)

# Migration order - init and tables run every time, sql files are tracked
MIGRATION_ORDER = ["init", "tables", "sql", "functions", "procedures"]
TRACKING_TABLE = "userprofiles.schema_migrations"


def get_db_root() -> Path:
    """Get database files root directory"""
    return Path(__file__).parent.parent / "db"


def apply_sql_file(cursor, file_path: Path) -> None:
    """Apply a SQL file"""
    try:
        sql_content = file_path.read_text(encoding="utf-8")
        cursor.execute(sql_content)
        logger.info("Applied migration", file=file_path.name)
    except Exception as e:
        logger.error("Failed to apply migration", file=file_path.name, error=str(e))
        raise


def ensure_tracking_table(cursor) -> None:
    """Ensure migration tracking table exists"""
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
            filename TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def is_migration_applied(cursor, filename: str) -> bool:
    """Check if a migration has been applied"""
    cursor.execute(f"SELECT 1 FROM {TRACKING_TABLE} WHERE filename = %s", (filename,))
    return cursor.fetchone() is not None


def mark_migration_applied(cursor, filename: str) -> None:
    """Mark a migration as applied"""
    cursor.execute(f"INSERT INTO {TRACKING_TABLE} (filename) VALUES (%s)", (filename,))


def run_migrations():
    """Run all migrations"""
    dsn = os.environ.get("PG_DSN")
    if not dsn:
        logger.error("PG_DSN environment variable is required")
        return False
    
    db_root = get_db_root()
    logger.info("Starting migrations", db_root=str(db_root))
    
    try:
        with psycopg.connect(dsn, autocommit=True) as conn:
            with conn.cursor() as cursor:
                # Ensure tracking table exists
                ensure_tracking_table(cursor)
                
                # Run migrations in order
                for stage in MIGRATION_ORDER:
                    stage_dir = db_root / stage
                    if not stage_dir.exists():
                        logger.info("Skipping stage - directory not found", stage=stage)
                        continue
                    
                    # Get all SQL files in this stage
                    sql_files = sorted(stage_dir.glob("**/*.sql"))
                    if not sql_files:
                        logger.info("No SQL files found in stage", stage=stage)
                        continue
                    
                    logger.info("Running migrations for stage", stage=stage, count=len(sql_files))
                    
                    for sql_file in sql_files:
                        filename = sql_file.name
                        
                        if stage == "sql":
                            # Only sql/ directory migrations are tracked
                            if is_migration_applied(cursor, filename):
                                logger.info("Skipping already applied migration", file=filename)
                                continue
                        
                        # Apply the migration
                        apply_sql_file(cursor, sql_file)
                        
                        # Mark as applied if it's a tracked migration
                        if stage == "sql":
                            mark_migration_applied(cursor, filename)
                
                logger.info("All migrations completed successfully")
                return True
                
    except Exception as e:
        logger.error("Migration failed", error=str(e))
        return False


if __name__ == "__main__":
    success = run_migrations()
    exit(0 if success else 1)