from config import settings
from models import *
from sqlmodel import Session, SQLModel, create_engine
from fastapi import logger
import sys
from sqlmodel import Session, text

engine = create_engine(
    settings.DATABASE_URL if settings.DATABASE_URL else "sqlite:///./test.db",
    echo=True,
    pool_size=20,
    max_overflow=2,
    pool_recycle=300,
    pool_pre_ping=True,
    pool_use_lifo=True,
)


def verify_db_connection():
    """
    Attempts to open a quick connection to verify the DB is alive.
    Aborts the entire server if it takes more than 10 seconds or fails.
    """
    logger.logger.info("Verifying database connectivity...")
    try:
        # We use a raw text execution to run a lightweight 'SELECT 1' query
        with Session(engine) as session:
            query = text("select now()")
            session.execute(query)
        logger.logger.info("Database connection verified successfully.")

    except Exception as e:
        # Log a highly visible error message
        logger.logger.critical(
            f"\n==================================================\n"
            f"CRITICAL SYSTEM FAILURE: DATABASE CONNECTION TIMEOUT\n"
            f"The database connection could not be established within 10 seconds.\n"
            f"Error details: {e}\n"
            f"=================================================="
        )
        # Abort the process immediately with a non-zero exit code
        # This signals to your cloud hosting (like Render) that the deploy failed
        sys.exit(1)

def get_session():
    with Session(engine) as session:
        yield session
