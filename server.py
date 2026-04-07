import uvicorn
import logging
from src.config import config

# Setup basic logging for the entry point
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    """
    Entry point for the Goldsprint server.
    Loads configuration and starts the uvicorn server.
    """
    logger.info(f"Starting Goldsprint SSS Server on {config.host}:{config.port}...")
    
    # Run the FastAPI app from src.main
    uvicorn.run(
        "src.main:app", 
        host=config.host, 
        port=config.port, 
        log_level="info",
        reload=False
    )
