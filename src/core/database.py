import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config.settings import settings

logger = logging.getLogger("alemeno.database")

# Create database engine
logger.info("Initializing SQLAlchemy database engine...")
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)
logger.info("SQLAlchemy database engine initialized successfully.")

# Session factory for DB transactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base model
Base = declarative_base()

def get_db():
    """
    Dependency helper to yield a database session.
    Ensures the session is closed after execution.
    """
    logger.debug("Opening new database session...")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.debug("Closing database session...")
        db.close()
