import uvicorn
from presentation.api.app import app
import os
from infrastructure.logging.config import configure_logging, log_startup_environment

if __name__ == "__main__":
    # Configure logging
    configure_logging()
    log_startup_environment()

    # Use port from environment variable if available, otherwise use 8889
    port = int(os.environ.get("PORT", 8889))
    uvicorn.run(app, host="0.0.0.0", port=port)
