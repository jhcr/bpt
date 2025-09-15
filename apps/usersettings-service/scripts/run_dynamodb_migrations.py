#!/usr/bin/env python3
"""
DynamoDB migration runner for UserSettings service

Runs Python migration files in order, tracking applied migrations in registry table.
"""

import os
import boto3
import importlib.util
from pathlib import Path
import time
from dotenv import load_dotenv
import structlog

# Setup basic logging
structlog.configure(
    processors=[structlog.stdlib.add_logger_name, structlog.stdlib.add_log_level, structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.stdlib.BoundLogger,
)

logger = structlog.get_logger(__name__)

# Load ../.env
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

REG_TABLE = os.getenv("USERSETTINGS_MIGRATIONS_TABLE", "usersettings_migrations_dev")
ddb = boto3.resource("dynamodb", endpoint_url=os.getenv("DYNAMODB_ENDPOINT_URL"))
reg = ddb.Table(REG_TABLE)


def applied(name):
    """Check if migration has been applied"""
    try:
        return reg.get_item(Key={"id": name}).get("Item") is not None
    except Exception:
        return False


def mark(name):
    """Mark migration as applied"""
    reg.put_item(Item={"id": name, "applied_at": int(time.time())})


def run_py(path):
    """Execute Python migration file"""
    spec = importlib.util.spec_from_file_location("m", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.up(ddb)


def main():
    """Run all pending migrations"""
    root = Path(__file__).parent.parent / "db" / "dynamodb" / "migrations"

    if not root.exists():
        logger.info("No migrations directory found", path=str(root))
        return True

    migrations = sorted(root.glob("*.py"))
    if not migrations:
        logger.info("No migration files found")
        return True

    logger.info("Starting DynamoDB migrations", count=len(migrations))

    for f in migrations:
        name = f.name
        if applied(name):
            logger.info("Skipping already applied migration", file=name)
            continue

        logger.info("Applying migration", file=name)
        run_py(str(f))
        mark(name)

    logger.info("All DynamoDB migrations completed successfully")
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
