import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.logging import setup_logging
from src.core.database import Base, engine
from src.api.routes import router as jobs_router

# Initialize the global logging configuration
setup_logging()
logger = logging.getLogger("alemeno.main")

# Automatically provision relational tables on system startup (zero-intervention blueprint)
logger.info("Executing automatic database schema migrations (Base.metadata.create_all)...")
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema migration validated and complete.")
except Exception as e:
    logger.exception("Failed to execute automatic database migrations on startup.")

# Instantiate FastAPI application
app = FastAPI(
    title="AI-Powered Transaction Processing Pipeline",
    description=(
        "A high-performance containerized backend pipeline that ingests dirty CSV "
        "exports, processes data out-of-band using Celery workers, performs anomaly "
        "detection, and applies Google Gemini LLM categorization and summaries."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoint controllers
app.include_router(jobs_router)

@app.get("/", tags=["Root"])
def root_status():
    """
    Direct service check index route.
    """
    return {
        "status": "healthy",
        "api_documentation": "/docs"
    }
