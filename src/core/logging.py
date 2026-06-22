import logging
import sys

# Define logging format
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"

def setup_logging(level: str = "INFO"):
    """
    Configure the global logger settings for the application.
    Allows dynamic level setting (e.g., DEBUG, INFO, WARNING).
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Overwrites any existing logging configurations
    )
    
    # Return a logger for the root module
    logger = logging.getLogger("alemeno")
    logger.info("Logging successfully initialized.")
    return logger
