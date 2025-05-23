import uvicorn
from presentation.api.app import app
import os

if __name__ == "__main__":
    # Use port from environment variable if available, otherwise use 8889
    port = int(os.environ.get("PORT", 8889))
    uvicorn.run(app, host="0.0.0.0", port=port)
